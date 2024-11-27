import json
import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    Task,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.text import Text
from rich.table import Table
from rich.console import Console
from rich.style import Style
from rich.panel import Panel

console = Console()

# 全域語言設定
CURRENT_LANG = "zh"

# 語言文字對照表
TRANSLATIONS = {
    "processing_start": {
        "zh": "開始處理檔案...",
        "en": "Starting file processing..."
    },
    "adjusting_structure": {
        "zh": "調整資料夾結構...",
        "en": "Adjusting folder structure..."
    },
    "moving_files": {
        "zh": "移動檔案中",
        "en": "Moving files"
    },
    "files": {
        "zh": "檔案",
        "en": "files"
    },
    "processing_files": {
        "zh": "處理檔案中",
        "en": "Processing files"
    },
    "converting": {
        "zh": "轉換中",
        "en": "Converting"
    },
    "creating_zip": {
        "zh": "建立ZIP檔案...",
        "en": "Creating ZIP file..."
    },
    "compressing_files": {
        "zh": "壓縮檔案中",
        "en": "Compressing files"
    },
    "moved_models": {
        "zh": "已將物品模型從 {} 移動到 {}",
        "en": "Moved item models from {} to {}"
    },
    "process_complete": {
        "zh": "處理完成！",
        "en": "Processing complete!"
    },
    "converted_files_count": {
        "zh": "已轉換 {} 個檔案",
        "en": "Converted {} files"
    },
    "output_file": {
        "zh": "輸出檔案",
        "en": "Output file"
    },
    "current_file": {
        "zh": "當前檔案：{}",
        "en": "Current file: {}"
    },
    "input_dir_error": {
        "zh": "錯誤：找不到輸入資料夾 '{}'",
        "en": "Error: Input directory '{}' not found"
    },
    "error_occurred": {
        "zh": "發生錯誤：{}",
        "en": "Error occurred: {}"
    },
    "speed_unit": {
        "zh": "檔案/秒",
        "en": "files/s"
    },
    "file_table_title": {
        "zh": "檔案處理報告",
        "en": "File Processing Report"
    },
    "file_name": {
        "zh": "檔案名稱",
        "en": "File Name"
    },
    "file_type": {
        "zh": "類型",
        "en": "Type"
    },
    "file_status": {
        "zh": "狀態",
        "en": "Status"
    },
    "status_converted": {
        "zh": "已轉換",
        "en": "Converted"
    },
    "status_copied": {
        "zh": "已複製",
        "en": "Copied"
    },
}

def get_text(key, *args):
    """獲取指定語言的文字"""
    text = TRANSLATIONS.get(key, {}).get(CURRENT_LANG, f"Missing translation: {key}")
    if args:
        return text.format(*args)
    return text

class CustomTimeElapsedColumn(TimeElapsedColumn):
    """自定義經過時間顯示"""
    def render(self, task: "Task") -> Text:
        elapsed = task.finished_time if task.finished else task.elapsed
        if elapsed is None:
            return Text("--:--", style="progress.elapsed")
        minutes, seconds = divmod(max(0, int(elapsed)), 60)
        return Text(f"{minutes:02d}:{seconds:02d}", style="progress.elapsed")

class CustomTransferSpeedColumn(TransferSpeedColumn):
    """自定義傳輸速度顯示"""
    def render(self, task: "Task") -> Text:
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text("?", style="progress.data.speed")
        return Text(f"{speed:.1f} {get_text('speed_unit')}", style="progress.data.speed")

class CustomProgressBar:
    """自定義進度條"""
    def __init__(self, total: int, description: str):
        self.total = total
        from rich.live import Live
        from rich.console import Group
        
        # 主進度條配置
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(complete_style="green", finished_style="green"),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            CustomTimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            CustomTransferSpeedColumn(),
            refresh_per_second=10,
            expand=True
        )
        
        # 為檔案資訊建立文字欄位
        self.file_text = Text("")
        
        # 建立群組來同時顯示進度條和檔案資訊
        self.group = Group(
            self.progress,
            self.file_text
        )
        
        # 使用 Live 來控制輸出
        self.live = Live(
            self.group,
            refresh_per_second=10,
            console=console
        )
        
        self.live.start()
        self.task = self.progress.add_task(description, total=self.total)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.live.stop()

    def advance(self, step: int = 1):
        self.progress.advance(self.task, step)

    def update_current_file(self, filename: str):
        self.file_text.plain = get_text("current_file", filename)

def count_files(directory):
    """計算目錄中的檔案總數"""
    total = 0
    for root, _, files in os.walk(directory):
        total += len(files)
    return total

def convert_json_format(input_json):
    """轉換JSON格式"""
    base_texture = input_json.get("textures", {}).get("layer0", "")
    
    if base_texture:
        if base_texture.startswith("minecraft:item/"):
            base_texture = f"minecraft:item/{base_texture.split('minecraft:item/')[-1]}"
        elif base_texture.startswith("item/"):
            base_texture = f"item/{base_texture.split('item/')[-1]}"
        elif not any(base_texture.startswith(prefix) for prefix in ["item/", "minecraft:item/"]):
            base_texture = f"item/{base_texture}"
    
    new_format = {
        "model": {
            "type": "range_dispatch",
            "property": "custom_model_data",
            "fallback": {
                "type": "model",
                "model": base_texture
            },
            "entries": []
        }
    }
    
    if "overrides" in input_json:
        for override in input_json["overrides"]:
            if "predicate" in override and "custom_model_data" in override["predicate"]:
                entry = {
                    "threshold": int(override["predicate"]["custom_model_data"]),
                    "model": {
                        "type": "model",
                        "model": override["model"]
                    }
                }
                new_format["model"]["entries"].append(entry)
    
    return new_format

def should_convert_json(json_data):
    """檢查JSON是否需要轉換"""
    if "overrides" not in json_data:
        return False
    
    for override in json_data.get("overrides", []):
        if "predicate" in override and "custom_model_data" in override["predicate"]:
            return True
    
    return False

def create_file_table(processed_files):
    """建立檔案處理報告表格"""
    table = Table(
        title=get_text("file_table_title"),
        show_header=True,
        header_style="bold magenta",
        border_style="blue",
        expand=True
    )
    
    table.add_column(get_text("file_name"), style="cyan", ratio=3)
    table.add_column(get_text("file_type"), style="green", justify="center", ratio=1)
    table.add_column(get_text("file_status"), style="yellow", justify="center", ratio=1)
    
    for file_info in processed_files:
        status_style = "green" if file_info["status"] == get_text("status_converted") else "blue"
        table.add_row(
            file_info["path"],
            file_info["type"],
            f"[{status_style}]{file_info['status']}[/{status_style}]"
        )
    
    return table

def adjust_folder_structure(base_dir):
    """調整資料夾結構"""
    assets_path = os.path.join(base_dir, "assets", "minecraft")
    models_item_path = os.path.join(assets_path, "models", "item")
    items_path = os.path.join(assets_path, "items")
    
    if os.path.exists(models_item_path):
        total_files = len(os.listdir(models_item_path))
        
        if total_files > 0:
            console.print(f"\n[cyan]{get_text('adjusting_structure')}[/cyan]")
            os.makedirs(items_path, exist_ok=True)
            
            with CustomProgressBar(total_files, get_text("moving_files")) as progress:
                for item in os.listdir(models_item_path):
                    src_path = os.path.join(models_item_path, item)
                    dst_path = os.path.join(items_path, item)
                    
                    if os.path.exists(dst_path):
                        backup_path = f"{dst_path}.bak"
                        shutil.move(dst_path, backup_path)
                    
                    shutil.move(src_path, dst_path)
                    progress.advance()
            
            shutil.rmtree(models_item_path)
            console.print(f"[green]{get_text('moved_models', models_item_path, items_path)}[/green]")

def process_directory(input_dir, output_dir):
    """處理目錄"""
    processed_files = []
    total_files = count_files(input_dir)
    
    os.makedirs(output_dir, exist_ok=True)
    
    with CustomProgressBar(total_files, get_text("processing_files")) as progress:
        for root, dirs, files in os.walk(input_dir):
            relative_path = os.path.relpath(root, input_dir)
            output_root = os.path.join(output_dir, relative_path)
            
            os.makedirs(output_root, exist_ok=True)
            
            for file in files:
                input_file = os.path.join(root, file)
                output_file = os.path.join(output_root, file)
                relative_path = os.path.relpath(input_file, input_dir)
                
                progress.update_current_file(relative_path)
                
                if file.lower().endswith('.json'):
                    try:
                        with open(input_file, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        
                        if should_convert_json(json_data):
                            converted_data = convert_json_format(json_data)
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(converted_data, f, indent=2)
                            processed_files.append({
                                "path": relative_path,
                                "type": "JSON",
                                "status": get_text("status_converted")
                            })
                            progress.advance()
                            continue
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        processed_files.append({
                            "path": relative_path,
                            "type": "JSON (Invalid)",
                            "status": get_text("status_copied")
                        })
                        shutil.copy2(input_file, output_file)
                        progress.advance()
                        continue
                
                file_ext = os.path.splitext(file)[1][1:].upper() or "FILE"
                processed_files.append({
                    "path": relative_path,
                    "type": file_ext,
                    "status": get_text("status_copied")
                })
                shutil.copy2(input_file, output_file)
                progress.advance()
    
    return processed_files

def create_zip(folder_path, zip_path):
    """建立ZIP檔案"""
    total_files = count_files(folder_path)
    
    console.print(f"\n[cyan]{get_text('creating_zip')}[/cyan]")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        with CustomProgressBar(total_files, get_text("compressing_files")) as progress:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, folder_path)
                    progress.update_current_file(arc_name)
                    zipf.write(file_path, arc_name)
                    progress.advance()

# converter.py (續上一部分)

def main(lang="zh"):
    """主程式"""
    global CURRENT_LANG
    CURRENT_LANG = lang
    
    input_dir = "input"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_output_dir = f"temp_output_{timestamp}"
    zip_filename = f"converted_{timestamp}.zip"
    
    try:
        if not os.path.exists(input_dir):
            console.print(Panel(
                get_text("input_dir_error", input_dir),
                style="red",
                expand=False
            ))
            return
        
        console.print(Panel(
            get_text("processing_start"),
            style="cyan",
            expand=False
        ))
        
        processed_files = process_directory(input_dir, temp_output_dir)
        adjust_folder_structure(temp_output_dir)
        create_zip(temp_output_dir, zip_filename)
        
        console.print(f"\n[green]{get_text('process_complete')}[/green]")
        
        # 顯示處理報告
        table = create_file_table(processed_files)
        console.print("\n", table)
        
        # 顯示總結資訊
        summary_table = Table.grid(expand=True)
        summary_table.add_column(style="cyan", justify="left")
        summary_table.add_column(style="green", justify="left")
        
        # 確保格式化字符串正確
        converted_count = sum(1 for f in processed_files if f["status"] == get_text("status_converted"))
        
        # 添加行，確保正確的格式化和對齊
        summary_table.add_row(
            f"[bold]{get_text('converted_files_count', converted_count)}[/bold]"
        )
        summary_table.add_row(
            f"[bold]{get_text('output_file')}:[/bold] {zip_filename}"
        )
        
        console.print("\n", Panel(
            summary_table,
            border_style="blue",
            expand=False
        ))
        
    except Exception as e:
        console.print(Panel(
            get_text("error_occurred", str(e)),
            style="red",
            expand=False
        ))
    
    finally:
        if os.path.exists(temp_output_dir):
            shutil.rmtree(temp_output_dir)

if __name__ == "__main__":
    main()