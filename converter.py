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
Version: 1.2.3
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

def create_crossbow_model_entry(base_model, pulling_states, arrow_model=None, firework_model=None):
    """
    Create a crossbow model entry with pulling states and ammunition types
    
    Args:
        base_model (str): Base model path for standby state
        pulling_states (list): List of dictionaries containing pulling states
        arrow_model (str, optional): Model path for arrow-loaded state
        firework_model (str, optional): Model path for firework-loaded state
        
    Returns:
        dict: Configured crossbow model entry with all states
    """
    # Create condition for using/pulling state
    model = {
        "type": "minecraft:condition",
        "property": "minecraft:using_item",
        "on_false": {
            "type": "minecraft:select",
            "property": "minecraft:charge_type",
            "fallback": {
                "type": "minecraft:model",
                "model": base_model
            },
            "cases": []
        },
        "on_true": {
            "type": "minecraft:range_dispatch",
            "property": "minecraft:crossbow/pull",
            "fallback": {
                "type": "minecraft:model",
                "model": pulling_states[0]["model"] if pulling_states else base_model
            },
            "entries": []
        }
    }

    # Add ammunition type cases
    cases = model["on_false"]["cases"]
    if arrow_model:
        cases.append({
            "model": {
                "type": "minecraft:model",
                "model": arrow_model
            },
            "when": "arrow"
        })
    if firework_model:
        cases.append({
            "model": {
                "type": "minecraft:model",
                "model": firework_model
            },
            "when": "rocket"
        })

    # Add pulling states
    if pulling_states:
        entries = model["on_true"]["entries"]
        for state in pulling_states[1:]:  # Skip first state as it's used in fallback
            entries.append({
                "threshold": state.get("pull", 0.0),
                "model": {
                    "type": "minecraft:model",
                    "model": state["model"]
                }
            })

    return model

def convert_crossbow_json_format(input_json):
    """
    Convert crossbow JSON format for Custom Model Data mode
    
    Args:
        input_json (dict): Original JSON data
        
    Returns:
        dict: Converted JSON in new format
    """
    # Extract base texture/model
    base_texture = input_json.get("textures", {}).get("layer0", "minecraft:item/crossbow")
    
    # Create new format structure
    new_format = {
        "model": {
            "type": "range_dispatch",
            "property": "custom_model_data",
            "fallback": {
                "type": "minecraft:model",
                "model": base_texture
            },
            "entries": []
        }
    }
    
    if "overrides" in input_json:
        # Group overrides by custom_model_data
        cmd_groups = {}
        
        for override in input_json["overrides"]:
            if "predicate" not in override or "model" not in override:
                continue
                
            predicate = override["predicate"]
            cmd = predicate.get("custom_model_data")
            
            if cmd is None:
                continue
                
            if cmd not in cmd_groups:
                cmd_groups[cmd] = {
                    "base": None,
                    "pulling_states": [],
                    "arrow": None,
                    "firework": None
                }
            
            # Categorize override based on predicates
            if "pulling" in predicate:
                pull_value = predicate.get("pull", 0.0)
                cmd_groups[cmd]["pulling_states"].append({
                    "pull": pull_value,
                    "model": override["model"]
                })
            elif "charged" in predicate:
                if predicate.get("firework", 0):
                    cmd_groups[cmd]["firework"] = override["model"]
                else:
                    cmd_groups[cmd]["arrow"] = override["model"]
            else:
                cmd_groups[cmd]["base"] = override["model"]
        
        # Create entries for each custom model data value
        for cmd, group in cmd_groups.items():
            # Sort pulling states by pull value
            pulling_states = sorted(group["pulling_states"], key=lambda x: x.get("pull", 0))
            base_model = group["base"] or pulling_states[0]["model"] if pulling_states else base_texture
            
            entry = {
                "threshold": int(cmd),
                "model": create_crossbow_model_entry(
                    base_model,
                    pulling_states,
                    group["arrow"],
                    group["firework"]
                )
            }
            new_format["model"]["entries"].append(entry)
    
    # Add any display settings from the original JSON
    if "display" in input_json:
        new_format["display"] = input_json["display"]
    
    return new_format

def is_crossbow_model(json_data):
    """
    Check if the JSON data is for a crossbow model
    
    Args:
        json_data (dict): JSON data to check
        
    Returns:
        bool: True if the data represents a crossbow model
    """
    # Check textures
    if "textures" in json_data and "layer0" in json_data["textures"]:
        texture = json_data["textures"]["layer0"]
        if "crossbow" in texture.lower():
            return True
    
    # Check overrides for crossbow-specific predicates
    if "overrides" in json_data:
        for override in json_data.get("overrides", []):
            predicate = override.get("predicate", {})
            if any(key in predicate for key in ["pulling", "charged", "firework"]):
                return True
    
    return False

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
    Convert JSON format for Custom Model Data mode with special handling for bows and crossbows
    
    Args:
        input_json (dict): Original JSON data to convert
        
    Returns:
        dict: Converted JSON in new format
    """
    # Extract and normalize base texture path
    base_texture = input_json.get("textures", {}).get("layer0", "")
    
    if base_texture:
        # Special handling for crossbow_standby
        if base_texture == "item/crossbow_standby":
            base_texture = "item/crossbow"
        
        # Normal path normalization
        if base_texture.startswith("minecraft:item/"):
            base_texture = base_texture
        elif base_texture.startswith("item/"):
            base_texture = f"minecraft:{base_texture}"
        elif not base_texture.startswith("minecraft:"):
            base_texture = f"minecraft:item/{base_texture}"

    # Create basic format structure
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

    # Add display settings if present
    if "display" in input_json:
        new_format["display"] = input_json["display"]

    if "overrides" not in input_json:
        return new_format

    # Detect model type and group overrides
    is_bow = base_texture == "minecraft:item/bow"
    is_crossbow = "crossbow" in base_texture.lower() if base_texture else False
    
    # Handle different model types
    if is_crossbow:
        # Group overrides by custom_model_data for crossbow
        cmd_groups = {}
        for override in input_json["overrides"]:
            if "predicate" not in override or "model" not in override:
                continue
                
            predicate = override["predicate"]
            cmd = predicate.get("custom_model_data")
            
            if cmd is None:
                continue
                
            if cmd not in cmd_groups:
                cmd_groups[cmd] = {
                    "base": None,
                    "pulling_states": [],
                    "arrow": None,
                    "firework": None
                }
            
            # Categorize crossbow override
            if "pulling" in predicate:
                pull_value = predicate.get("pull", 0.0)
                cmd_groups[cmd]["pulling_states"].append({
                    "pull": pull_value,
                    "model": override["model"]
                })
            elif "charged" in predicate:
                if predicate.get("firework", 0):
                    cmd_groups[cmd]["firework"] = override["model"]
                else:
                    cmd_groups[cmd]["arrow"] = override["model"]
            else:
                cmd_groups[cmd]["base"] = override["model"]
        
        # Create crossbow entries
        for cmd, group in cmd_groups.items():
            pulling_states = sorted(group["pulling_states"], key=lambda x: x.get("pull", 0))
            base_model = group["base"] or pulling_states[0]["model"] if pulling_states else base_texture
            
            entry = {
                "threshold": int(cmd),
                "model": {
                    "type": "minecraft:condition",
                    "property": "minecraft:using_item",
                    "on_false": {
                        "type": "minecraft:select",
                        "property": "minecraft:charge_type",
                        "fallback": {
                            "type": "minecraft:model",
                            "model": base_model
                        },
                        "cases": []
                    },
                    "on_true": {
                        "type": "minecraft:range_dispatch",
                        "property": "minecraft:crossbow/pull",
                        "fallback": {
                            "type": "minecraft:model",
                            "model": pulling_states[0]["model"] if pulling_states else base_model
                        },
                        "entries": []
                    }
                }
            }

            # Add ammunition cases
            cases = entry["model"]["on_false"]["cases"]
            if group["arrow"]:
                cases.append({
                    "model": {
                        "type": "minecraft:model",
                        "model": group["arrow"]
                    },
                    "when": "arrow"
                })
            if group["firework"]:
                cases.append({
                    "model": {
                        "type": "minecraft:model",
                        "model": group["firework"]
                    },
                    "when": "rocket"
                })

            # Add pulling states
            if pulling_states:
                entries = entry["model"]["on_true"]["entries"]
                for state in pulling_states[1:]:
                    entries.append({
                        "threshold": state.get("pull", 0.0),
                        "model": {
                            "type": "minecraft:model",
                            "model": state["model"]
                        }
                    })

            new_format["model"]["entries"].append(entry)

    elif is_bow:
        # Group overrides by custom_model_data for bow
        cmd_groups = {}
        
        for override in input_json["overrides"]:
            if "predicate" not in override or "model" not in override:
                continue
                
            predicate = override["predicate"]
            cmd = predicate.get("custom_model_data")
            
            if cmd is None:
                continue
                
            if cmd not in cmd_groups:
                cmd_groups[cmd] = {
                    "base": None,
                    "pulling_states": []
                }
            
            if "pulling" in predicate:
                pull_value = predicate.get("pull", 0.0)
                cmd_groups[cmd]["pulling_states"].append({
                    "pull": pull_value,
                    "model": override["model"]
                })
            else:
                cmd_groups[cmd]["base"] = override["model"]
        
        # Create bow entries
        for cmd, group in cmd_groups.items():
            pulling_states = sorted(group["pulling_states"], key=lambda x: x.get("pull", 0))
            base_model = group["base"] or pulling_states[0]["model"] if pulling_states else base_texture
            
            if base_model:
                entry = {
                    "threshold": int(cmd),
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
                }
                new_format["model"]["entries"].append(entry)

    else:
        # Handle normal items
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

def get_base_model_path(overrides, cmd):
    """
    Get the base model path from overrides for a specific custom_model_data value
    
    Args:
        overrides (list): List of override entries
        cmd (int): Custom model data value to look for
        
    Returns:
        str: Base model path without special states, or None if not found
    """
    for override in overrides:
        predicate = override.get("predicate", {})
        if predicate.get("custom_model_data") != cmd:
            continue
            
        # Check if this is a base model (no special states)
        if not any(key in predicate for key in ["charged", "firework", "pulling", "pull"]):
            return override["model"]
    
    return None

def create_bow_json(base_model, pulling_states):
    """
    Create bow JSON structure in the new format
    
    Args:
        base_model (str): Base model path
        pulling_states (list): List of pulling states with pull values and models
    
    Returns:
        dict: Configured bow JSON structure
    """
    # Sort pulling states by pull value and exclude base model
    pulling_states = sorted(
        [state for state in pulling_states if state["model"] != base_model],
        key=lambda x: x["pull"]
    )
    
    return {
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
                "entries": [
                    {
                        "threshold": state["pull"],
                        "model": {
                            "type": "minecraft:model",
                            "model": state["model"]
                        }
                    } for state in pulling_states
                ]
            }
        }
    }

def convert_item_model_format(json_data, output_path):
    """
    Convert JSON format for Item Model mode with special handling for bows and crossbows
    
    Args:
        json_data (dict): Original JSON data containing model overrides
        output_path (str): Base path for output files
    """
    if "overrides" not in json_data or not json_data["overrides"]:
        return None

    # Group overrides by custom_model_data
    cmd_groups = {}
    base_texture = json_data.get("textures", {}).get("layer0", "")
    is_bow = "bow" in base_texture and "crossbow" not in base_texture
    is_crossbow = "crossbow" in base_texture

    if is_bow or is_crossbow:
        # First find the base model path for each CMD
        for cmd in {override["predicate"]["custom_model_data"] 
                   for override in json_data["overrides"] 
                   if "predicate" in override and "custom_model_data" in override["predicate"]}:
            
            base_model = get_base_model_path(json_data["overrides"], cmd)
            if base_model:
                if cmd not in cmd_groups:
                    cmd_groups[cmd] = {
                        "base": base_model,
                        "pulling_states": [],
                        "arrow": None,
                        "firework": None
                    }

                # Group other states for this CMD
                for override in json_data["overrides"]:
                    predicate = override.get("predicate", {})
                    if predicate.get("custom_model_data") != cmd:
                        continue

                    if "pulling" in predicate:
                        if "pull" in predicate:
                            cmd_groups[cmd]["pulling_states"].append({
                                "pull": predicate["pull"],
                                "model": override["model"]
                            })
                    elif "charged" in predicate:
                        if predicate.get("firework", 0):
                            cmd_groups[cmd]["firework"] = override["model"]
                        else:
                            cmd_groups[cmd]["arrow"] = override["model"]

        # Process each group that has a base model
        for cmd, group in cmd_groups.items():
            if not group["base"]:
                continue

            if is_crossbow:
                # Create crossbow JSON structure
                crossbow_json = {
                    "model": {
                        "type": "minecraft:condition",
                        "property": "minecraft:using_item",
                        "on_false": {
                            "type": "minecraft:select",
                            "property": "minecraft:charge_type",
                            "fallback": {
                                "type": "minecraft:model",
                                "model": group["base"]
                            },
                            "cases": []
                        },
                        "on_true": {
                            "type": "minecraft:range_dispatch",
                            "property": "minecraft:crossbow/pull",
                            "fallback": {
                                "type": "minecraft:model",
                                "model": group["pulling_states"][0]["model"] if group["pulling_states"] else group["base"]
                            },
                            "entries": []
                        }
                    }
                }

                # Add ammunition cases
                cases = crossbow_json["model"]["on_false"]["cases"]
                if group["arrow"]:
                    cases.append({
                        "model": {
                            "type": "minecraft:model",
                            "model": group["arrow"]
                        },
                        "when": "arrow"
                    })
                if group["firework"]:
                    cases.append({
                        "model": {
                            "type": "minecraft:model",
                            "model": group["firework"]
                        },
                        "when": "rocket"
                    })

                # Add pulling states
                pulling_states = sorted(group["pulling_states"], key=lambda x: x["pull"])
                if len(pulling_states) > 1:  # Skip first state as it's used in fallback
                    for state in pulling_states[1:]:
                        crossbow_json["model"]["on_true"]["entries"].append({
                            "threshold": state["pull"],
                            "model": {
                                "type": "minecraft:model",
                                "model": state["model"]
                            }
                        })

                # Save crossbow JSON
                if ":" in group["base"]:
                    namespace, path = group["base"].split(":", 1)
                    file_name = os.path.join(output_path, namespace, path) + ".json"
                else:
                    file_name = os.path.join(output_path, group["base"] + ".json")
                
                os.makedirs(os.path.dirname(file_name), exist_ok=True)
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(crossbow_json, f, indent=2)

            else:  # bow
                # Create bow JSON structure
                bow_json = {
                    "model": {
                        "type": "minecraft:condition",
                        "property": "minecraft:using_item",
                        "on_false": {
                            "type": "minecraft:model",
                            "model": group["base"]
                        },
                        "on_true": {
                            "type": "minecraft:range_dispatch",
                            "property": "minecraft:use_duration",
                            "scale": 0.05,
                            "fallback": {
                                "type": "minecraft:model",
                                "model": group["base"]
                            },
                            "entries": []
                        }
                    }
                }

                # Add pulling states
                pulling_states = sorted(group["pulling_states"], key=lambda x: x["pull"])
                if pulling_states:
                    for state in pulling_states:
                        if state["model"] != group["base"]:  # Skip if it's the same as base model
                            bow_json["model"]["on_true"]["entries"].append({
                                "threshold": state["pull"],
                                "model": {
                                    "type": "minecraft:model",
                                    "model": state["model"]
                                }
                            })

                # Save bow JSON using the base model path
                if ":" in group["base"]:
                    namespace, path = group["base"].split(":", 1)
                    file_name = os.path.join(output_path, namespace, path) + ".json"
                else:
                    file_name = os.path.join(output_path, group["base"] + ".json")
                
                os.makedirs(os.path.dirname(file_name), exist_ok=True)
                with open(file_name, 'w', encoding='utf-8') as f:
                    json.dump(bow_json, f, indent=2)

    else:
        # Handle normal items
        for override in json_data["overrides"]:
            if "predicate" in override and "custom_model_data" in override["predicate"]:
                model_path = override["model"]
                if ":" in model_path:
                    namespace, path = model_path.split(":", 1)
                    file_name = os.path.join(output_path, namespace, path) + ".json"
                else:
                    file_name = os.path.join(output_path, model_path + ".json")
                
                os.makedirs(os.path.dirname(file_name), exist_ok=True)
                
                new_json = {
                    "model": {
                        "type": "model",
                        "model": model_path
                    }
                }
                
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
    Only processes files directly in the models/item directory,
    ignoring any files in subdirectories.
    
    Args:
        input_dir (str): Source directory containing files to convert
        output_dir (str): Destination directory for converted files
        
    Returns:
        list: List of processed file information dictionaries
    """
    processed_files = []
    
    # First copy all files to maintain complete structure
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
    
    # Process only direct JSON files in models/item directory
    models_item_dir = os.path.join(output_dir, "assets", "minecraft", "models", "item")
    items_dir = os.path.join(output_dir, "assets", "minecraft", "items")
    
    if os.path.exists(models_item_dir):
        os.makedirs(items_dir, exist_ok=True)
        
        # Get only direct JSON files (not in subdirectories)
        direct_json_files = [f for f in os.listdir(models_item_dir) 
                           if os.path.isfile(os.path.join(models_item_dir, f)) 
                           and f.lower().endswith('.json')]
        
        total_files = len(direct_json_files)
        processed_count = 0
        
        # Set up progress tracking
        if is_gui_console(console) and CustomProgress:
            progress = CustomProgress(console)
        else:
            progress = create_standard_progress()
        
        with progress as progress_ctx:
            task = progress_ctx.add_task(get_text("processing_files"), total=total_files)
            
            # Process each direct JSON file
            for file in direct_json_files:
                if is_gui_console(console):
                    console.print(get_text("current_file", file))
                
                src_path = os.path.join(models_item_dir, file)
                dst_path = os.path.join(items_dir, file)
                
                try:
                    # Create backup if file exists
                    if os.path.exists(dst_path):
                        backup_path = f"{dst_path}.bak"
                        shutil.move(dst_path, backup_path)
                    
                    # Move file to new location
                    shutil.move(src_path, dst_path)
                    
                    # Process the moved file
                    with open(dst_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                    
                    if should_convert_json(json_data):
                        convert_item_model_format(json_data, items_dir)
                        os.remove(dst_path)  # Remove the original file after conversion
                        processed_files.append({
                            "path": os.path.relpath(dst_path, output_dir),
                            "type": "JSON",
                            "status": get_text("status_converted")
                        })
                    else:
                        processed_files.append({
                            "path": os.path.relpath(dst_path, output_dir),
                            "type": "JSON",
                            "status": get_text("status_copied")
                        })
                        
                except Exception as e:
                    console.print(f"[red]{get_text('error_occurred', str(e))}[/red]")
                
                processed_count += 1
                progress_ctx.update(task, completed=processed_count)
            
            # Only remove models/item if it's empty
            if os.path.exists(models_item_dir) and not os.listdir(models_item_dir):
                shutil.rmtree(models_item_dir)
    
    return processed_files

def adjust_folder_structure(base_dir):
    """
    Adjust the folder structure by moving only the direct files from models/item to items
    Subdirectories in models/item will be left untouched
    
    Args:
        base_dir (str): Base directory to adjust structure in
    """
    assets_path = os.path.join(base_dir, "assets", "minecraft")
    models_item_path = os.path.join(assets_path, "models", "item")
    items_path = os.path.join(assets_path, "items")
    
    if os.path.exists(models_item_path):
        # Only count direct files in models/item directory
        total_files = len([f for f in os.listdir(models_item_path) 
                         if os.path.isfile(os.path.join(models_item_path, f))])
        
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
                
                # Only process files directly in models/item
                for item in os.listdir(models_item_path):
                    src_path = os.path.join(models_item_path, item)
                    
                    # Skip if it's a directory
                    if os.path.isdir(src_path):
                        continue
                        
                    if is_gui_console(console):
                        console.print(get_text("current_file", item))
                    
                    dst_path = os.path.join(items_path, item)
                    
                    # Handle existing file
                    if os.path.exists(dst_path):
                        backup_path = f"{dst_path}.bak"
                        shutil.move(dst_path, backup_path)
                    
                    # Move file
                    shutil.move(src_path, dst_path)
                    progress_ctx.update(task, advance=1)
            
            # Only remove models/item if it's empty
            if os.path.exists(models_item_path) and not os.listdir(models_item_path):
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