import json
import os
import shutil
import zipfile
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

# 全域變數初始化
CURRENT_LANG = "zh"
console = Console()
CustomProgress = None

# 檢查是否為GUI控制台
def is_gui_console(console_obj):
    """檢查是否為GUI控制台"""
    return hasattr(console_obj, 'status_label') and hasattr(console_obj, 'progress_bar')

# 創建標準進度條
def create_standard_progress():
    """創建標準的命令列進度條"""
    return Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(complete_style="green", finished_style="green"),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        TransferSpeedColumn(),
        refresh_per_second=10,
        expand=True
    )

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
    "processing_files": {
        "zh": "處理檔案中",
        "en": "Processing files"
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

def count_files(directory):
    """計算目錄中的檔案總數"""
    total = 0
    for root, _, files in os.walk(directory):
        total += len(files)
    return total

def convert_json_format(input_json):
    """轉換JSON格式 (Custom Model Data 模式)"""
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

def convert_item_model_format(json_data, output_path):
    """轉換物品模型格式 (Item Model 模式)"""
    # 檢查是否包含必要的字段
    if "overrides" not in json_data or not json_data["overrides"]:
        return None
    
    # 遍歷所有 override
    for override in json_data["overrides"]:
        if "predicate" in override and "custom_model_data" in override["predicate"] and "model" in override:
            model_path = override["model"]
            
            # 解析模型路徑
            if ":" in model_path:
                # 處理 "a:b" 格式
                namespace, path = model_path.split(":", 1)
                target_dir = os.path.join(output_path, namespace)
            else:
                # 處理 "a/b" 格式
                parts = model_path.split("/")
                target_dir = os.path.join(output_path, *parts[:-1])
            
            # 確保目標目錄存在
            os.makedirs(target_dir, exist_ok=True)
            
            # 構建新的 JSON 內容
            new_json = {
                "model": {
                    "type": "model",
                    "model": model_path
                }
            }
            
            # 構建目標文件路徑
            if ":" in model_path:
                # 對於 "a:b" 格式，保持完整路徑
                file_name = os.path.join(output_path, model_path.replace(":", "/")) + ".json"
            else:
                # 對於 "a/b" 格式，直接使用完整路徑
                file_name = os.path.join(output_path, model_path + ".json")
            
            # 確保目標文件的目錄存在
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            
            # 寫入新文件
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(new_json, f, indent=2)

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

def process_directory(input_dir, output_dir):
    """處理目錄（Custom Model Data 模式）"""
    processed_files = []
    
    # 計算需要處理的 JSON 檔案數量
    json_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.json'):
                json_files.append(os.path.join(root, file))
    
    total_files = len(json_files)
    processed_count = 0
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 檢查是否為GUI模式
    if is_gui_console(console) and CustomProgress:
        progress = CustomProgress(console)
    else:
        progress = create_standard_progress()
    
    with progress as progress_ctx:
        task = progress_ctx.add_task(get_text("processing_files"), total=total_files)
        
        # 複製所有檔案到輸出目錄
        for root, dirs, files in os.walk(input_dir):
            relative_path = os.path.relpath(root, input_dir)
            output_root = os.path.join(output_dir, relative_path)
            
            os.makedirs(output_root, exist_ok=True)
            
            for file in files:
                input_file = os.path.join(root, file)
                output_file = os.path.join(output_root, file)
                relative_path = os.path.relpath(input_file, input_dir)
                
                try:
                    shutil.copy2(input_file, output_file)
                    if not file.lower().endswith('.json'):
                        processed_files.append({
                            "path": relative_path,
                            "type": "Other",
                            "status": get_text("status_copied")
                        })
                except Exception as e:
                    console.print(f"[red]{get_text('error_occurred', str(e))}[/red]")
        
        # 處理 JSON 檔案
        for json_file in json_files:
            input_file = json_file
            relative_path = os.path.relpath(input_file, input_dir)
            output_file = os.path.join(output_dir, relative_path)
            
            if is_gui_console(console):
                console.print(get_text("current_file", relative_path))
            
            try:
                with open(input_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                if should_convert_json(json_data):
                    converted_data = convert_json_format(json_data)
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(converted_data, f, indent=4)
                    
                    processed_files.append({
                        "path": relative_path,
                        "type": "JSON",
                        "status": get_text("status_converted")
                    })
                else:
                    processed_files.append({
                        "path": relative_path,
                        "type": "JSON",
                        "status": get_text("status_copied")
                    })
            except Exception as e:
                console.print(f"[red]{get_text('error_occurred', str(e))}[/red]")
            
            processed_count += 1
            progress_ctx.update(task, completed=processed_count)
    
    return processed_files

def process_directory_item_model(input_dir, output_dir):
    """處理目錄（Item Model 轉換模式）"""
    processed_files = []
    
    # 計算需要處理的 JSON 檔案數量
    json_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.json'):
                json_files.append(os.path.join(root, file))
    
    total_files = len(json_files)
    processed_count = 0
    
    # 確保輸出目錄存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 檢查是否為GUI模式
    if is_gui_console(console) and CustomProgress:
        progress = CustomProgress(console)
    else:
        progress = create_standard_progress()
    
    with progress as progress_ctx:
        task = progress_ctx.add_task(get_text("processing_files"), total=total_files)
        
        # 首先複製所有檔案
        for root, dirs, files in os.walk(input_dir):
            relative_path = os.path.relpath(root, input_dir)
            output_root = os.path.join(output_dir, relative_path)
            
            os.makedirs(output_root, exist_ok=True)
            
            for file in files:
                if is_gui_console(console):
                    console.print(get_text("current_file", file))
                
                input_file = os.path.join(root, file)
                output_file = os.path.join(output_root, file)
                shutil.copy2(input_file, output_file)
                
                if not file.lower().endswith('.json'):
                    processed_files.append({
                        "path": os.path.relpath(input_file, input_dir),
                        "type": "Other",
                        "status": get_text("status_copied")
                    })
        
        # 處理 models/item 目錄中的 JSON 檔案
        models_item_dir = os.path.join(output_dir, "assets", "minecraft", "models", "item")
        items_dir = os.path.join(output_dir, "assets", "minecraft", "items")
        
        if os.path.exists(models_item_dir):
            os.makedirs(items_dir, exist_ok=True)
            processed_item_jsons = []
            
            # 首先移動所有 JSON 檔案
            for root, _, files in os.walk(models_item_dir):
                for file in files:
                    if file.lower().endswith('.json'):
                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(items_dir, file)
                        
                        if os.path.exists(dst_path):
                            backup_path = f"{dst_path}.bak"
                            shutil.move(dst_path, backup_path)
                        
                        shutil.move(src_path, dst_path)
                        processed_item_jsons.append(dst_path)
            
            # 然後處理已移動的 JSON 檔案
            for json_path in processed_item_jsons:
                if is_gui_console(console):
                    console.print(get_text("current_file", os.path.basename(json_path)))
                
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    
                    # 檢查是否需要轉換
                    if should_convert_json(json_data):
                        # 轉換並建立新的檔案
                        convert_item_model_format(json_data, items_dir)
                        # 移除原始檔案
                        os.remove(json_path)
                        processed_files.append({
                            "path": os.path.relpath(json_path, output_dir),
                            "type": "JSON",
                            "status": get_text("status_converted")
                        })
                    else:
                        processed_files.append({
                            "path": os.path.relpath(json_path, output_dir),
                            "type": "JSON",
                            "status": get_text("status_copied")
                        })
                except Exception as e:
                    console.print(f"[red]{get_text('error_occurred', str(e))}[/red]")
                
                processed_count += 1
                progress_ctx.update(task, completed=processed_count)
            
            # 移除空的 models/item 目錄
            shutil.rmtree(models_item_dir)
    
    return processed_files

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
            
            # 檢查是否為GUI模式
            if is_gui_console(console) and CustomProgress:
                progress = CustomProgress(console)
            else:
                progress = create_standard_progress()
            
            with progress as progress_ctx:
                task = progress_ctx.add_task(get_text("moving_files"), total=total_files)
                
                for item in os.listdir(models_item_path):
                    if is_gui_console(console):
                        console.print(get_text("current_file", item))
                    
                    src_path = os.path.join(models_item_path, item)
                    dst_path = os.path.join(items_path, item)
                    
                    if os.path.exists(dst_path):
                        backup_path = f"{dst_path}.bak"
                        shutil.move(dst_path, backup_path)
                    
                    shutil.move(src_path, dst_path)
                    progress_ctx.update(task, advance=1)
            
            shutil.rmtree(models_item_path)
            console.print(f"[green]{get_text('moved_models', models_item_path, items_path)}[/green]")

def create_zip(folder_path, zip_path):
    """建立ZIP檔案"""
    total_files = count_files(folder_path)
    
    console.print(f"\n[cyan]{get_text('creating_zip')}[/cyan]")
    
    # 檢查是否為GUI模式
    if is_gui_console(console) and CustomProgress:
        progress = CustomProgress(console)
    else:
        progress = create_standard_progress()
    
    with progress as progress_ctx:
        task = progress_ctx.add_task(get_text("compressing_files"), total=total_files)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, folder_path)
                    
                    if is_gui_console(console):
                        console.print(get_text("current_file", arc_name))
                    
                    zipf.write(file_path, arc_name)
                    progress_ctx.update(task, advance=1)

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
            return False
        
        # 檢查input目錄是否為空
        if not any(os.scandir(input_dir)):
            console.print(Panel(
                get_text("no_files_found", input_dir),
                style="yellow",
                expand=False
            ))
            return False
        
        console.print(Panel(
            get_text("processing_start"),
            style="cyan",
            expand=False
        ))
        
        # 建立臨時目錄
        os.makedirs(temp_output_dir, exist_ok=True)
        
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
        
        converted_count = sum(1 for f in processed_files if f["status"] == get_text("status_converted"))
        
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
        
        return True
        
    except Exception as e:
        console.print(Panel(
            get_text("error_occurred", str(e)),
            style="red",
            expand=False
        ))
        return False
    
    finally:
        if os.path.exists(temp_output_dir):
            try:
                shutil.rmtree(temp_output_dir)
            except Exception:
                pass

if __name__ == "__main__":
    main()