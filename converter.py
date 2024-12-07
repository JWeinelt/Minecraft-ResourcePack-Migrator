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
Version: 1.1
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

def convert_json_format(input_json):
    """
    Convert JSON format for Custom Model Data mode
    
    Takes a Minecraft resource pack JSON file in the old format and converts it
    to the new format using range_dispatch. Handles texture paths and custom
    model data entries.
    
    Args:
        input_json (dict): Original JSON data to convert
        
    Returns:
        dict: Converted JSON data in the new format with:
            - Normalized texture paths
            - Range dispatch model type
            - Custom model data entries
    """
    # Extract and normalize base texture path
    base_texture = input_json.get("textures", {}).get("layer0", "")
    
    if base_texture:
        if base_texture.startswith("minecraft:item/"):
            base_texture = f"minecraft:item/{base_texture.split('minecraft:item/')[-1]}"
        elif base_texture.startswith("item/"):
            base_texture = f"item/{base_texture.split('item/')[-1]}"
        elif not any(base_texture.startswith(prefix) for prefix in ["item/", "minecraft:item/"]):
            base_texture = f"item/{base_texture}"
    
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
    
    # Convert overrides to new format entries
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
    """
    Convert JSON format for Item Model mode
    
    Processes item model JSON files, creating new model files in the appropriate
    directory structure. Handles both namespaced and non-namespaced paths.
    
    Args:
        json_data (dict): Original JSON data containing model overrides
        output_path (str): Base path for output files
        
    Returns:
        None
        
    Notes:
        Creates new JSON files in the output directory for each valid model override
    """
    # Verify required fields
    if "overrides" not in json_data or not json_data["overrides"]:
        return None
    
    # Process each override entry
    for override in json_data["overrides"]:
        if "predicate" in override and "custom_model_data" in override["predicate"] and "model" in override:
            model_path = override["model"]
            
            # Parse model path and determine target directory
            if ":" in model_path:
                # Handle namespaced paths (e.g., "minecraft:block/stone")
                namespace, path = model_path.split(":", 1)
                target_dir = os.path.join(output_path, namespace)
            else:
                # Handle regular paths (e.g., "block/stone")
                parts = model_path.split("/")
                target_dir = os.path.join(output_path, *parts[:-1])
            
            # Create target directory
            os.makedirs(target_dir, exist_ok=True)
            
            # Create new JSON content
            new_json = {
                "model": {
                    "type": "model",
                    "model": model_path
                }
            }
            
            # Determine and create output file path
            if ":" in model_path:
                file_name = os.path.join(output_path, model_path.replace(":", "/")) + ".json"
            else:
                file_name = os.path.join(output_path, model_path + ".json")
            
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            
            # Write converted JSON file
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