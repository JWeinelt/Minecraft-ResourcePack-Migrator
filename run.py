import subprocess
import sys
import os
import time
import json
from pathlib import Path

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
        "zh": "\n找不到需要轉換的檔案！",
        "en": "\nNo files found for conversion!"
    },
    "please_check": {
        "zh": "請確認：",
        "en": "Please check:"
    },
    "check_json_exists": {
        "zh": "1. 輸入資料夾中有 JSON 檔案",
        "en": "1. JSON files exist in input folder"
    },
    "check_json_format": {
        "zh": "2. JSON 檔案包含 'overrides' 和 'custom_model_data' 欄位",
        "en": "2. JSON files contain 'overrides' and 'custom_model_data' fields"
    },
    "check_file_location": {
        "zh": "3. 檔案放在正確的位置（{}/ 資料夾中）",
        "en": "3. Files are in correct location (in {} folder)"
    },
    "files_found": {
        "zh": "\n找到 {} 個可轉換的檔案：",
        "en": "\nFound {} convertible files:"
    },
    "continue_prompt": {
        "zh": "\n是否繼續轉換？[Y/n] ",
        "en": "\nContinue conversion? [Y/n] "
    },
    "conversion_cancelled": {
        "zh": "已取消轉換",
        "en": "Conversion cancelled"
    },
    "env_check_complete": {
        "zh": "\n環境檢查完成，開始執行轉換程式...\n",
        "en": "\nEnvironment check complete, starting conversion...\n"
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
        "zh": "\n按 Enter 鍵結束程式...",
        "en": "\nPress Enter to exit..."
    },
    "title": {
        "zh": "=== Minecraft 資源包更新工具 (1.14 ~ 1.21.4+) ===\n",
        "en": "=== Minecraft Resource Pack Migrator (1.14 ~ 1.21.4+) ===\n"
    }
}

def get_text(key, lang="zh", *args):
    """
    獲取指定語言的文字
    
    Args:
        key (str): 文字索引
        lang (str): 語言代碼 (zh/en)
        *args: 格式化參數
    Returns:
        str: 翻譯後的文字
    """
    text = TRANSLATIONS.get(key, {}).get(lang, f"Missing translation: {key}")
    if args:
        return text.format(*args)
    return text

def check_and_install_package(package_name, lang="zh"):
    """
    檢查並安裝必要的套件
    """
    try:
        __import__(package_name)
        return True
    except ImportError:
        print(get_text("installing_package", lang, package_name))
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            return True
        except subprocess.CalledProcessError:
            print(get_text("package_install_error", lang, package_name))
            return False

def find_convertible_files(directory):
    """
    搜尋可轉換的JSON檔案
    """
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

def main(lang="zh"):
    """
    主程式：檢查環境、檢查檔案、安裝套件並執行轉換程式
    """
    print(get_text("checking_python", lang))
    if sys.version_info < (3, 6):
        print(get_text("python_version_error", lang))
        return False

    input_dir = "input"
    if not os.path.exists(input_dir):
        print(get_text("input_dir_error", lang, input_dir))
        print(get_text("create_input_dir", lang, input_dir))
        return False

    print(get_text("searching_files", lang))
    convertible_files = find_convertible_files(input_dir)
    
    if not convertible_files:
        print(get_text("no_files_found", lang))
        print(get_text("please_check", lang))
        print(get_text("check_json_exists", lang))
        print(get_text("check_json_format", lang))
        print(get_text("check_file_location", lang, input_dir))
        return False
    
    print(get_text("files_found", lang, len(convertible_files)))
    for file in convertible_files:
        print(f"- {file}")

    print(get_text("continue_prompt", lang), end='')
    response = input().strip().lower()
    if response and response != 'y':
        print(get_text("conversion_cancelled", lang))
        return False

    required_packages = ['tqdm']
    for package in required_packages:
        if not check_and_install_package(package, lang):
            return False

    print(get_text("env_check_complete", lang))
    time.sleep(1)

    try:
        import converter
        converter.main()
        return True
    except ImportError:
        print(get_text("converter_not_found", lang))
        print(get_text("check_converter_location", lang))
        return False
    except Exception as e:
        print(get_text("execution_error", lang, str(e)))
        return False

if __name__ == "__main__":
    # 設定終端機編碼為 UTF-8（主要是為了 Windows）
    if sys.platform.startswith('win'):
        os.system('chcp 65001')
    
    # 決定使用的語言（這裡可以根據需求修改，例如從系統設定或使用者輸入獲取）
    print("Choose language / 選擇語言:")
    print("1. 中文")
    print("2. English")
    lang_choice = input("Please enter 1 or 2 / 請輸入 1 或 2: ").strip()
    
    lang = "zh" if lang_choice == "1" else "en"
    
    print("\n" + get_text("title", lang))
    
    success = main(lang)
    
    if sys.platform.startswith('win'):
        print(get_text("press_enter", lang), end='')
        input()
    
    sys.exit(0 if success else 1)