import json
import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

# 語言文字對照表
TRANSLATIONS = {
    "processing_start": {
        "zh": "開始處理檔案...\n",
        "en": "Starting file processing...\n"
    },
    "adjusting_structure": {
        "zh": "\n調整資料夾結構...",
        "en": "\nAdjusting folder structure..."
    },
    "moving_files": {
        "zh": "移動檔案",
        "en": "Moving files"
    },
    "files": {
        "zh": "檔案",
        "en": "files"
    },
    "processing_files": {
        "zh": "處理檔案",
        "en": "Processing files"
    },
    "converting": {
        "zh": "轉換",
        "en": "Converting"
    },
    "creating_zip": {
        "zh": "\n建立ZIP檔案...",
        "en": "\nCreating ZIP file..."
    },
    "compressing_files": {
        "zh": "壓縮檔案",
        "en": "Compressing files"
    },
    "moved_models": {
        "zh": "已將物品模型從 {} 移動到 {}",
        "en": "Moved item models from {} to {}"
    },
    "process_complete": {
        "zh": "\n處理完成！",
        "en": "\nProcessing complete!"
    },
    "converted_files_count": {
        "zh": "已轉換 {} 個檔案:",
        "en": "Converted {} files:"
    },
    "output_file": {
        "zh": "\n輸出檔案: {}",
        "en": "\nOutput file: {}"
    },
    "input_dir_error": {
        "zh": "錯誤：找不到輸入資料夾 '{}'",
        "en": "Error: Input directory '{}' not found"
    },
    "error_occurred": {
        "zh": "發生錯誤：{}",
        "en": "Error occurred: {}"
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

def count_files(directory):
    """
    計算目錄中的檔案總數
    """
    total = 0
    for root, _, files in os.walk(directory):
        total += len(files)
    return total

def convert_json_format(input_json):
    """
    將Minecraft的物品模型JSON格式轉換為新格式
    
    Args:
        input_json (dict): 原始JSON格式的字典
    Returns:
        dict: 轉換後的新格式JSON字典
    """
    # 獲取基本材質資訊並處理路徑
    base_texture = input_json.get("textures", {}).get("layer0", "")
    
    # 處理材質路徑
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
    """
    檢查JSON檔案是否需要轉換
    """
    if "overrides" not in json_data:
        return False
    
    for override in json_data["overrides"]:
        if "predicate" in override and "custom_model_data" in override["predicate"]:
            return True
    
    return False

def adjust_folder_structure(base_dir, lang="zh"):
    """
    調整資料夾結構：將 models/item 移動到 items
    """
    assets_path = os.path.join(base_dir, "assets", "minecraft")
    models_item_path = os.path.join(assets_path, "models", "item")
    items_path = os.path.join(assets_path, "items")
    
    if os.path.exists(models_item_path):
        total_files = len(os.listdir(models_item_path))
        
        if total_files > 0:
            print(get_text("adjusting_structure", lang))
            os.makedirs(items_path, exist_ok=True)
            
            # 使用tqdm顯示移動檔案的進度
            for item in tqdm(os.listdir(models_item_path), 
                           desc=get_text("moving_files", lang),
                           unit=get_text("files", lang)):
                src_path = os.path.join(models_item_path, item)
                dst_path = os.path.join(items_path, item)
                
                if os.path.exists(dst_path):
                    backup_path = f"{dst_path}.bak"
                    shutil.move(dst_path, backup_path)
                
                shutil.move(src_path, dst_path)
            
            shutil.rmtree(models_item_path)
            print(get_text("moved_models", lang, models_item_path, items_path))

def process_directory(input_dir, output_dir, lang="zh"):
    """
    處理整個資料夾的JSON檔案
    """
    converted_files = []
    total_files = count_files(input_dir)
    
    with tqdm(total=total_files, 
             desc=get_text("processing_files", lang),
             unit=get_text("files", lang)) as pbar:
        os.makedirs(output_dir, exist_ok=True)
        
        for root, dirs, files in os.walk(input_dir):
            relative_path = os.path.relpath(root, input_dir)
            output_root = os.path.join(output_dir, relative_path)
            
            os.makedirs(output_root, exist_ok=True)
            
            for file in files:
                input_file = os.path.join(root, file)
                output_file = os.path.join(output_root, file)
                
                if file.lower().endswith('.json'):
                    try:
                        with open(input_file, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        
                        if should_convert_json(json_data):
                            converted_data = convert_json_format(json_data)
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(converted_data, f, indent=2)
                            converted_files.append(os.path.relpath(input_file, input_dir))
                            pbar.set_postfix({get_text("converting", lang): os.path.basename(file)})
                            pbar.update(1)
                            continue
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        shutil.copy2(input_file, output_file)
                        pbar.update(1)
                        continue
                
                shutil.copy2(input_file, output_file)
                pbar.update(1)
    
    return converted_files

def create_zip(folder_path, zip_path, lang="zh"):
    """
    將資料夾壓縮為ZIP檔案
    """
    total_files = count_files(folder_path)
    
    print(get_text("creating_zip", lang))
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        with tqdm(total=total_files,
                desc=get_text("compressing_files", lang),
                unit=get_text("files", lang)) as pbar:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, folder_path)
                    zipf.write(file_path, arc_name)
                    pbar.update(1)

def main(lang="zh"):
    """
    主程式
    """
    input_dir = "input"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_output_dir = f"temp_output_{timestamp}"
    zip_filename = f"converted_{timestamp}.zip"
    
    try:
        if not os.path.exists(input_dir):
            print(get_text("input_dir_error", lang, input_dir))
            return
        
        print(get_text("processing_start", lang))
        
        converted_files = process_directory(input_dir, temp_output_dir, lang)
        adjust_folder_structure(temp_output_dir, lang)
        create_zip(temp_output_dir, zip_filename, lang)
        
        print(get_text("process_complete", lang))
        print(get_text("converted_files_count", lang, len(converted_files)))
        for file in converted_files:
            print(f"- {file}")
        print(get_text("output_file", lang, zip_filename))
        
    except Exception as e:
        print(get_text("error_occurred", lang, str(e)))
    
    finally:
        if os.path.exists(temp_output_dir):
            shutil.rmtree(temp_output_dir)

if __name__ == "__main__":
    main()