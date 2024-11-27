import subprocess
import sys
import os
import time
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

console = Console()

# 語言文字對照表
TRANSLATIONS = {
    "checking_python": {
        "zh": "檢查 Python 環境...",
        "en": "Checking Python environment..."
    },
    "python_version_error": {
        "zh": "錯誤：需要 Python 3.6 或更新版本",
        "en": "Error: Python 3.6 or newer is required"
    },
    "installing_package": {
        "zh": "正在安裝必要套件 {}...",
        "en": "Installing required package {}..."
    },
    "package_install_error": {
        "zh": "錯誤：無法安裝 {}",
        "en": "Error: Unable to install {}"
    },
    "input_dir_error": {
        "zh": "錯誤：找不到輸入資料夾 '{}'",
        "en": "Error: Input directory '{}' not found"
    },
    "create_input_dir": {
        "zh": "請建立 '{}' 資料夾並放入要轉換的檔案",
        "en": "Please create '{}' directory and place files to convert"
    },
    "searching_files": {
        "zh": "搜尋可轉換的檔案...",
        "en": "Searching for convertible files..."
    },
    "no_files_found": {
        "zh": "找不到需要轉換的檔案！",
        "en": "No files found for conversion!"
    },
    "please_check": {
        "zh": "請檢查：",
        "en": "Please check:"
    },
    "check_list_title": {
        "zh": "檢查清單",
        "en": "Checklist"
    },
    "check_json_exists": {
        "zh": "輸入資料夾中有 JSON 檔案",
        "en": "JSON files exist in input folder"
    },
    "check_json_format": {
        "zh": "JSON 檔案包含 'overrides' 和 'custom_model_data' 欄位",
        "en": "JSON files contain 'overrides' and 'custom_model_data' fields"
    },
    "check_file_location": {
        "zh": "檔案放在正確的位置（{}/ 資料夾中）",
        "en": "Files are in correct location (in {} folder)"
    },
    "found_files_title": {
        "zh": "可轉換的檔案",
        "en": "Convertible Files"
    },
    "continue_prompt": {
        "zh": "是否繼續轉換？[Y/n]",
        "en": "Continue conversion? [Y/n]"
    },
    "conversion_cancelled": {
        "zh": "已取消轉換",
        "en": "Conversion cancelled"
    },
    "env_check_complete": {
        "zh": "環境檢查完成，開始執行轉換程式...",
        "en": "Environment check complete, starting conversion..."
    },
    "converter_not_found": {
        "zh": "錯誤：找不到轉換程式 (converter.py)",
        "en": "Error: Converter program (converter.py) not found"
    },
    "check_converter_location": {
        "zh": "請確認 converter.py 檔案在正確的位置",
        "en": "Please ensure converter.py is in the correct location"
    },
    "execution_error": {
        "zh": "執行過程中發生錯誤：{}",
        "en": "Error during execution: {}"
    },
    "press_enter": {
        "zh": "按 Enter 鍵結束程式...",
        "en": "Press Enter to exit..."
    },
    "title": {
        "zh": "Minecraft 資源包更新工具 (1.14 ~ 1.21.4+)",
        "en": "Minecraft Resource Pack Migrator (1.14 ~ 1.21.4+)"
    },
    "choose_language": {
        "zh": "選擇語言",
        "en": "Choose Language"
    },
    "column_number": {
        "zh": "序號",
        "en": "No."
    },
    "column_file_path": {
        "zh": "檔案路徑",
        "en": "File Path"
    }
}

def get_text(key, lang="zh", *args):
    """獲取指定語言的文字"""
    text = TRANSLATIONS.get(key, {}).get(lang, f"Missing translation: {key}")
    if args:
        return text.format(*args)
    return text

def check_and_install_package(package_name, lang="zh"):
    """檢查並安裝必要的套件"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        console.print(f"[yellow]{get_text('installing_package', lang, package_name)}[/yellow]")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            return True
        except subprocess.CalledProcessError:
            console.print(f"[red]{get_text('package_install_error', lang, package_name)}[/red]")
            return False

def find_convertible_files(directory):
    """搜尋可轉換的JSON檔案"""
    convertible_files = []
    
    if not os.path.exists(directory):
        return convertible_files
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.json'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    
                    if "overrides" in json_data:
                        for override in json_data.get("overrides", []):
                            if "predicate" in override and "custom_model_data" in override["predicate"]:
                                convertible_files.append(os.path.relpath(file_path, directory))
                                break
                except (json.JSONDecodeError, UnicodeDecodeError, Exception):
                    continue
    
    return convertible_files

def display_convertible_files(files, lang):
    """顯示可轉換的檔案清單"""
    if not files:
        return
    
    table = Table(
        title=get_text("found_files_title", lang),
        show_header=True,
        border_style="blue",
        expand=True
    )
    
    # 使用翻譯後的列名
    table.add_column(get_text("column_number", lang), style="cyan", justify="center")
    table.add_column(get_text("column_file_path", lang), style="green")
    
    for i, file in enumerate(files, 1):
        table.add_row(str(i), file)
    
    console.print("\n", table)

def display_checklist(input_dir, lang):
    """顯示檢查清單"""
    table = Table(
        title=get_text("check_list_title", lang),
        show_header=False,
        border_style="yellow",
        expand=True
    )
    
    table.add_column(style="yellow")
    
    table.add_row(f"1. {get_text('check_json_exists', lang)}")
    table.add_row(f"2. {get_text('check_json_format', lang)}")
    table.add_row(f"3. {get_text('check_file_location', lang, input_dir)}")
    
    console.print("\n", table)

def main(lang="zh"):
    """主程式"""
    console.print(f"[cyan]{get_text('checking_python', lang)}[/cyan]")
    if sys.version_info < (3, 6):
        console.print(Panel(
            get_text("python_version_error", lang),
            style="red",
            expand=False
        ))
        return False

    input_dir = "input"
    if not os.path.exists(input_dir):
        console.print(Panel(
            f"{get_text('input_dir_error', lang, input_dir)}\n{get_text('create_input_dir', lang, input_dir)}",
            style="red",
            expand=False
        ))
        return False

    console.print(f"[cyan]{get_text('searching_files', lang)}[/cyan]")
    convertible_files = find_convertible_files(input_dir)
    
    if not convertible_files:
        console.print(f"\n[yellow]{get_text('no_files_found', lang)}[/yellow]")
        display_checklist(input_dir, lang)
        return False
    
    display_convertible_files(convertible_files, lang)

    if not Prompt.ask(
        f"\n[cyan]{get_text('continue_prompt', lang)}[/cyan]",
        default="y"
    ).lower() == "y":
        console.print(f"[yellow]{get_text('conversion_cancelled', lang)}[/yellow]")
        return False

    required_packages = ['rich']
    for package in required_packages:
        if not check_and_install_package(package, lang):
            return False

    console.print(Panel(
        get_text("env_check_complete", lang),
        style="green",
        expand=False
    ))
    time.sleep(1)

    try:
        import converter
        converter.CURRENT_LANG = lang
        converter.main(lang)
        return True
    except ImportError:
        console.print(Panel(
            f"{get_text('converter_not_found', lang)}\n{get_text('check_converter_location', lang)}",
            style="red",
            expand=False
        ))
        return False
    except Exception as e:
        console.print(Panel(
            get_text("execution_error", lang, str(e)),
            style="red",
            expand=False
        ))
        return False

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        os.system('chcp 65001')
    
    console.print(Panel(
        get_text("choose_language", "zh") + " / " + get_text("choose_language", "en"),
        style="cyan",
        expand=False
    ))
    console.print("1. [green]中文[/green]")
    console.print("2. [blue]English[/blue]")
    
    lang_choice = Prompt.ask(
        "Please enter 1 or 2 / 請輸入 1 或 2",
        default="1"
    ).strip()
    
    lang = "zh" if lang_choice == "1" else "en"
    
    console.print(Panel(
        get_text("title", lang),
        style="bold cyan",
        expand=False
    ))
    
    success = main(lang)
    
    if sys.platform.startswith('win'):
        input(f"\n{get_text('press_enter', lang)}")
    
    sys.exit(0 if success else 1)