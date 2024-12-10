"""
Minecraft Resource Pack Converter Module

This module handles the conversion of Minecraft resource pack files between different formats.
It supports both Custom Model Data and Item Model conversion modes with comprehensive features:

Features:
- Bilingual support (English/Chinese)
- Both GUI and console interfaces
- Progress tracking and reporting
- ZIP file handling
- Directory structure management
- Detailed processing reports
- Error handling and recovery

The module can be used both as a standalone command-line tool and as part of a GUI application.

Author: RiceChen_
Version: 1.2.1
"""

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

# Global variables initialization
CURRENT_LANG = "zh"  # Default language setting
console = Console()   # Console instance for output handling
CustomProgress = None # Custom progress tracking class (set by GUI)

def is_gui_console(console_obj):
    """
    Check if the console object is a GUI console instance
    
    Args:
        console_obj: Console object to check
        
    Returns:
        bool: True if console is GUI console (has status_label and progress_bar), False otherwise
    """
    return hasattr(console_obj, 'status_label') and hasattr(console_obj, 'progress_bar')

def create_standard_progress():
    """
    Create a standard command-line progress bar with rich formatting
    
    Creates a rich.progress.Progress instance with columns for:
    - Task description with blue bold text
    - Green progress bar
    - Task completion percentage
    - Items completed count
    - Time elapsed
    - Separator
    - Time remaining
    - Transfer speed
    
    Returns:
        Progress: Configured progress bar instance
    """
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

# Language translation mapping
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
    """
    Retrieve translated text for the current language
    
    Args:
        key (str): Translation key to look up
        *args: Optional format arguments for the text
    
    Returns:
        str: Translated text, formatted with args if provided
    """
    text = TRANSLATIONS.get(key, {}).get(CURRENT_LANG, f"Missing translation: {key}")
    if args:
        return text.format(*args)
    return text

def count_files(directory):
    """
    Count total number of files in a directory and its subdirectories
    
    Args:
        directory (str): Path to the directory to scan
        
    Returns:
        int: Total number of files found in directory tree
    """
    total = 0
    for root, _, files in os.walk(directory):
        total += len(files)
    return total

def create_bow_model_entry(pulling_states, base_model):
    """
    Create a bow model entry with pulling states
    
    Args:
        pulling_states (list): List of dictionaries containing pulling states
        base_model (str): Base model path for non-pulling state
    
    Returns:
        dict: Configured bow model entry
    """
    return {
        "type": "minecraft:condition",
        "property": "minecraft:using_item",
        "on_false": {
            "type": "minecraft:model",
            "model": base_model
        },
        "on_true": {
            "type": "minecraft:range_dispatch",
            "property": "minecraft:use_duration",
            "scale": 0.05,
            "fallback": {
                "type": "minecraft:model",
                "model": pulling_states[0]["model"] if pulling_states else base_model
            },
            "entries": [
                {
                    "threshold": state.get("pull", 0.0),
                    "model": {
                        "type": "minecraft:model",
                        "model": state["model"]
                    }
                } for state in pulling_states[1:]
            ]
        }
    }

def convert_json_format(input_json):
    """
    Convert JSON format for Custom Model Data mode with special handling for bows
    """
    # Extract and normalize base texture path
    base_texture = input_json.get("textures", {}).get("layer0", "")
    
    if base_texture:
        if base_texture.startswith("minecraft:item/"):
            base_texture = base_texture
        elif base_texture.startswith("item/"):
            base_texture = f"minecraft:{base_texture}"
        elif not base_texture.startswith("minecraft:"):
            base_texture = f"minecraft:item/{base_texture}"
    
    # Create new format structure
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
    
    # Check if this is a bow model
    is_bow = base_texture == "minecraft:item/bow"
    
    if "overrides" in input_json:
        # Group overrides by custom_model_data
        cmd_groups = {}
        vanilla_pulling_states = []
        
        for override in input_json["overrides"]:
            if "predicate" not in override or "model" not in override:
                continue
                
            predicate = override["predicate"]
            cmd = predicate.get("custom_model_data")
            
            if cmd is None:
                # Handle vanilla pulling states
                if "pulling" in predicate:
                    pull_value = predicate.get("pull", 0.0)
                    vanilla_pulling_states.append({
                        "pull": pull_value,
                        "model": override["model"]
                    })
                continue
            
            if cmd not in cmd_groups:
                cmd_groups[cmd] = {
                    "base": None,
                    "pulling_states": []
                }
            
            # Group pulling states and base model
            if "pulling" in predicate:
                pull_value = predicate.get("pull", 0.0)
                cmd_groups[cmd]["pulling_states"].append({
                    "pull": pull_value,
                    "model": override["model"]
                })
            else:
                cmd_groups[cmd]["base"] = override["model"]
        
        # Create entries for each custom model data value
        for cmd, group in cmd_groups.items():
            if is_bow:
                # Sort pulling states by pull value
                pulling_states = sorted(group["pulling_states"], key=lambda x: x.get("pull", 0))
                base_model = group["base"] or pulling_states[0]["model"] if pulling_states else None
                
                if base_model:
                    entry = {
                        "threshold": int(cmd),
                        "model": create_bow_model_entry(pulling_states, base_model)
                    }
                    new_format["model"]["entries"].append(entry)
            else:
                # Handle non-bow items normally
                if group["base"]:
                    entry = {
                        "threshold": int(cmd),
                        "model": {
                            "type": "model",
                            "model": group["base"]
                        }
                    }
                    new_format["model"]["entries"].append(entry)
    
    # Add any display settings from the original JSON
    if "display" in input_json:
        new_format["display"] = input_json["display"]
    
    return new_format

def is_bow_model(model_path):
    """
    Check if the model path is for a bow
    
    Args:
        model_path (str): Model path to check
        
    Returns:
        bool: True if the model is a bow variant
    """
    # Check for common bow model patterns
    bow_patterns = [
        "/bow0", "/bow1", "/bow2", "/bow_pulling_0", 
        "/bow_pulling_1", "/bow_pulling_2", "_bow0", 
        "_bow1", "_bow2"
    ]
    return any(pattern in model_path for pattern in bow_patterns)

def group_bow_models(overrides):
    """
    Group bow models by their base name and pulling states
    
    Args:
        overrides (list): List of model overrides
        
    Returns:
        dict: Grouped bow models with base path and pulling states
    """
    bow_groups = {}
    
    for override in overrides:
        if "predicate" not in override or "model" not in override:
            continue
            
        model_path = override["model"]
        if not is_bow_model(model_path):
            continue
            
        # Extract base path (remove _pulling or number suffix)
        base_path = model_path.rsplit('/', 1)[0]
        base_model = model_path.rsplit('/', 1)[1]
        
        if base_path not in bow_groups:
            bow_groups[base_path] = {
                "base_model": None,
                "pulling_states": []
            }
        
        predicate = override["predicate"]
        if "pulling" in predicate:
            pull_value = predicate.get("pull", 0.0)
            bow_groups[base_path]["pulling_states"].append({
                "pull": pull_value,
                "model": model_path
            })
        else:
            # This is the base model (bow0)
            bow_groups[base_path]["base_model"] = model_path
            
    return bow_groups

def convert_item_model_format(json_data, output_path):
    """
    Convert JSON format for Item Model mode with special handling for bows
    
    Args:
        json_data (dict): Original JSON data containing model overrides
        output_path (str): Base path for output files
    """
    if "overrides" not in json_data or not json_data["overrides"]:
        return None
        
    # Group bow models
    bow_groups = group_bow_models(json_data["overrides"])
    
    # Process each group of bow models
    for base_path, group in bow_groups.items():
        if not group["base_model"] or not group["pulling_states"]:
            continue
            
        # Sort pulling states by pull value
        pulling_states = sorted(group["pulling_states"], key=lambda x: x.get("pull", 0.0))
        base_model = group["base_model"]
        
        # Create the bow model JSON
        bow_json = {
            "model": {
                "type": "minecraft:condition",
                "property": "minecraft:using_item",
                "on_false": {
                    "type": "minecraft:model",
                    "model": base_model
                },
                "on_true": {
                    "type": "minecraft:range_dispatch",
                    "property": "minecraft:use_duration",
                    "scale": 0.05,
                    "fallback": {
                        "type": "minecraft:model",
                        "model": base_model
                    },
                    "entries": []
                }
            }
        }
        
        # Add pulling states entries
        for state in pulling_states:
            entry = {
                "threshold": state["pull"],
                "model": {
                    "type": "minecraft:model",
                    "model": state["model"]
                }
            }
            bow_json["model"]["on_true"]["entries"].append(entry)
        
        # Determine output file path
        if ":" in base_model:
            namespace, path = base_model.split(":", 1)
            file_name = os.path.join(output_path, namespace, path) + ".json"
        else:
            file_name = os.path.join(output_path, base_model + ".json")
            
        # Create output directory if needed
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        
        # Write converted JSON file
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(bow_json, f, indent=2)
    
    # Process non-bow models normally
    for override in json_data["overrides"]:
        if "predicate" in override and "custom_model_data" in override["predicate"]:
            model_path = override["model"]
            
            # Skip bow models as they were already processed
            if is_bow_model(model_path):
                continue
                
            # Process normal item models as before
            if ":" in model_path:
                namespace, path = model_path.split(":", 1)
                target_dir = os.path.join(output_path, namespace)
            else:
                parts = model_path.split("/")
                target_dir = os.path.join(output_path, *parts[:-1])
            
            os.makedirs(target_dir, exist_ok=True)
            
            new_json = {
                "model": {
                    "type": "model",
                    "model": model_path
                }
            }
            
            if ":" in model_path:
                file_name = os.path.join(output_path, model_path.replace(":", "/")) + ".json"
            else:
                file_name = os.path.join(output_path, model_path + ".json")
            
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(new_json, f, indent=2)

def should_convert_json(json_data):
    """
    Check if a JSON file needs conversion
    
    Args:
        json_data (dict): JSON data to check
        
    Returns:
        bool: True if the JSON contains custom model data overrides
    """
    if "overrides" not in json_data:
        return False
    
    for override in json_data.get("overrides", []):
        if "predicate" in override and "custom_model_data" in override["predicate"]:
            return True
    
    return False

def create_file_table(processed_files):
    """
    Create a formatted table showing file processing results
    
    Args:
        processed_files (list): List of dictionaries containing file processing information
            Each dict should have keys:
            - path: File path
            - type: File type
            - status: Processing status
            
    Returns:
        Table: Rich formatted table showing processing results
    """
    table = Table(
        title=get_text("file_table_title"),
        show_header=True,
        header_style="bold magenta",
        border_style="blue",
        expand=True
    )
    
    # Configure table columns
    table.add_column(get_text("file_name"), style="cyan", ratio=3)
    table.add_column(get_text("file_type"), style="green", justify="center", ratio=1)
    table.add_column(get_text("file_status"), style="yellow", justify="center", ratio=1)
    
    # Add file entries to table
    for file_info in processed_files:
        status_style = "green" if file_info["status"] == get_text("status_converted") else "blue"
        table.add_row(
            file_info["path"],
            file_info["type"],
            f"[{status_style}]{file_info['status']}[/{status_style}]"
        )
    
    return table

def process_directory(input_dir, output_dir):
    """
    Process directory in Custom Model Data mode
    
    Converts all compatible JSON files in the input directory to the new format
    while preserving the directory structure. Tracks progress and handles errors.
    
    Args:
        input_dir (str): Source directory containing files to convert
        output_dir (str): Destination directory for converted files
        
    Returns:
        list: List of processed file information dictionaries
    """
    processed_files = []
    
    # Find all JSON files to process
    json_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.json'):
                json_files.append(os.path.join(root, file))
    
    total_files = len(json_files)
    processed_count = 0
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Create appropriate progress bar
    if is_gui_console(console) and CustomProgress:
        progress = CustomProgress(console)
    else:
        progress = create_standard_progress()
    
    with progress as progress_ctx:
        task = progress_ctx.add_task(get_text("processing_files"), total=total_files)
        
        # Copy all files to output directory
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
        
        # Process JSON files
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
    """
    Process directory in Item Model mode
    
    Similar to process_directory but handles the special requirements of
    item model conversion, including directory structure changes.
    
    Args:
        input_dir (str): Source directory containing files to convert
        output_dir (str): Destination directory for converted files
        
    Returns:
        list: List of processed file information dictionaries
    """
    processed_files = []
    
    # Find JSON files
    json_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith('.json'):
                json_files.append(os.path.join(root, file))
    
    total_files = len(json_files)
    processed_count = 0
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Create progress bar
    if is_gui_console(console) and CustomProgress:
        progress = CustomProgress(console)
    else:
        progress = create_standard_progress()
    
    with progress as progress_ctx:
        task = progress_ctx.add_task(get_text("processing_files"), total=total_files)
        
        # First copy all files
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
        
        # Process models/item directory JSON files
        models_item_dir = os.path.join(output_dir, "assets", "minecraft", "models", "item")
        items_dir = os.path.join(output_dir, "assets", "minecraft", "items")
        
        if os.path.exists(models_item_dir):
            os.makedirs(items_dir, exist_ok=True)
            processed_item_jsons = []
            
            # First move all JSON files to new location
            for root, _, files in os.walk(models_item_dir):
                for file in files:
                    if file.lower().endswith('.json'):
                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(items_dir, file)
                        
                        # Create backup if file exists
                        if os.path.exists(dst_path):
                            backup_path = f"{dst_path}.bak"
                            shutil.move(dst_path, backup_path)
                        
                        shutil.move(src_path, dst_path)
                        processed_item_jsons.append(dst_path)
            
            # Then process moved JSON files
            for json_path in processed_item_jsons:
                if is_gui_console(console):
                    console.print(get_text("current_file", os.path.basename(json_path)))
                
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    
                    # Convert if needed
                    if should_convert_json(json_data):
                        convert_item_model_format(json_data, items_dir)
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
            
            # Remove empty models/item directory
            shutil.rmtree(models_item_dir)
    
    return processed_files

def adjust_folder_structure(base_dir):
    """
    Adjust the folder structure by moving files from models/item to items
    
    Args:
        base_dir (str): Base directory to adjust structure in
    """
    assets_path = os.path.join(base_dir, "assets", "minecraft")
    models_item_path = os.path.join(assets_path, "models", "item")
    items_path = os.path.join(assets_path, "items")
    
    if os.path.exists(models_item_path):
        total_files = len(os.listdir(models_item_path))
        
        if total_files > 0:
            console.print(f"\n[cyan]{get_text('adjusting_structure')}[/cyan]")
            os.makedirs(items_path, exist_ok=True)
            
            # Set up progress tracking
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
    """
    Create a ZIP archive from a folder
    
    Args:
        folder_path (str): Path to the folder to compress
        zip_path (str): Output path for the ZIP file
    """
    total_files = count_files(folder_path)
    
    console.print(f"\n[cyan]{get_text('creating_zip')}[/cyan]")
    
    # Set up progress tracking
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
    """
    Main program entry point
    
    Args:
        lang (str): Language code ('zh' or 'en')
        
    Returns:
        bool: True if conversion successful, False otherwise
    """
    global CURRENT_LANG
    CURRENT_LANG = lang
    
    input_dir = "input"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_output_dir = f"temp_output_{timestamp}"
    zip_filename = f"converted_{timestamp}.zip"
    
    try:
        # Validate input directory
        if not os.path.exists(input_dir):
            console.print(Panel(
                get_text("input_dir_error", input_dir),
                style="red",
                expand=False
            ))
            return False
        
        # Check if input directory is empty
        if not any(os.scandir(input_dir)):
            console.print(Panel(
                get_text("no_files_found", input_dir),
                style="yellow",
                expand=False
            ))
            return False
        
        # Start processing
        console.print(Panel(
            get_text("processing_start"),
            style="cyan",
            expand=False
        ))
        
        # Create temporary directory
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # Process files
        processed_files = process_directory(input_dir, temp_output_dir)
        adjust_folder_structure(temp_output_dir)
        create_zip(temp_output_dir, zip_filename)
        
        # Show completion message
        console.print(f"\n[green]{get_text('process_complete')}[/green]")
        
        # Display processing report
        table = create_file_table(processed_files)
        console.print("\n", table)
        
        # Show summary information
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