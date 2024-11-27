import sys
import os
import shutil
import zipfile
import tempfile
import errno
import stat
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import converter
import json
import threading
from rich.console import Console

# 語言文字對照表
TRANSLATIONS = {
    "title": {
        "zh": "Minecraft 資源包更新工具 (1.14 ~ 1.21.4+)",
        "en": "Minecraft Resource Pack Migrator (1.14 ~ 1.21.4+)"
    },
    "language_selection": {
        "zh": "語言選擇 | Language Selection",
        "en": "語言選擇 | Language Selection"
    },
    "file_list": {
        "zh": "檔案列表",
        "en": "File List"
    },
    "choose_folder": {
        "zh": "選擇資料夾",
        "en": "Choose Folder"
    },
    "choose_zip": {
        "zh": "選擇ZIP",
        "en": "Choose ZIP"
    },
    "start_convert": {
        "zh": "開始轉換",
        "en": "Start Convert"
    },
    "clear_files": {
        "zh": "清除檔案",
        "en": "Clear Files"
    },
    "confirm_exit": {
        "zh": "確認離開",
        "en": "Confirm Exit"
    },
    "confirm_exit_processing": {
        "zh": "正在處理檔案中，確定要離開嗎？\n檔案處理將會中斷。",
        "en": "Processing files, are you sure to exit?\nFile processing will be interrupted."
    },
    "confirm_exit_normal": {
        "zh": "確定要離開程式嗎？",
        "en": "Are you sure to exit?"
    },
    "warning": {
        "zh": "警告",
        "en": "Warning"
    },
    "select_files_first": {
        "zh": "請先選擇檔案",
        "en": "Please select files first"
    },
    "complete": {
        "zh": "完成",
        "en": "Complete"
    },
    "conversion_complete": {
        "zh": "轉換完成！輸出檔案：{}",
        "en": "Conversion complete! Output file: {}"
    },
    "select_folder": {
        "zh": "選擇資料夾",
        "en": "Select Folder"
    },
    "select_zip": {
        "zh": "選擇ZIP檔案",
        "en": "Select ZIP File"
    },
    "extracting": {
        "zh": "正在解壓縮...",
        "en": "Extracting..."
    },
    "copying_files": {
        "zh": "正在複製檔案...",
        "en": "Copying files..."
    },
    "error": {
        "zh": "錯誤",
        "en": "Error"
    },
    "processing": {
        "zh": "處理中...",
        "en": "Processing..."
    },
    "conversion_failed": {
        "zh": "轉換失敗：{}",
        "en": "Conversion failed: {}"
    },
    "output_folder": {
        "zh": "輸出資料夾",
        "en": "Output Folder"
    },
    "open_output_folder": {
        "zh": "開啟輸出資料夾",
        "en": "Open Output Folder"
    },
    "change_output_folder": {
        "zh": "變更輸出位置",
        "en": "Change Output Location"
    },
    "select_output_folder": {
        "zh": "選擇輸出資料夾",
        "en": "Select Output Folder"
    }
}

def get_text(key, lang):
    """獲取指定語言的文字"""
    return TRANSLATIONS.get(key, {}).get(lang, f"Missing translation: {key}")

class GuiConsole(Console):
    """GUI控制台類，用於處理進度顯示和輸出"""
    def __init__(self, status_label, progress_bar, progress_var):
        super().__init__()
        self.status_label = status_label
        self.progress_bar = progress_bar
        self.progress_var = progress_var
        self.current_task = None
        self.total = 0
        self.completed = 0

    def print(self, *args, **kwargs):
        """處理輸出訊息，更新狀態標籤"""
        message = " ".join(str(arg) for arg in args)
        # 移除 rich 格式標記
        for tag in ['cyan', 'green', 'yellow', 'red', 'bold']:
            message = message.replace(f'[{tag}]', '').replace(f'[/{tag}]', '')
        
        self.status_label.after(0, self.status_label.config, {"text": message})
        
        # 重置進度條
        if any(x in message.lower() for x in ["processing files", "moving files", "compressing files"]):
            self.reset_progress()

    def reset_progress(self):
        """重置進度"""
        self.completed = 0
        self.total = 0
        self.progress_var.set(0)

    def update(self, completed=None, total=None, advance=1):
        """更新進度條"""
        if total is not None:
            self.total = total
        if completed is not None:
            self.completed = completed
        else:
            self.completed += advance

        if self.total > 0:
            progress = (self.completed / self.total) * 100
            self.progress_var.set(progress)

class CustomProgress:
    """自定義進度追蹤類"""
    def __init__(self, console):
        self.console = console

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add_task(self, description, total=None):
        if total is not None:
            self.console.reset_progress()
            self.console.total = total
        return 0

    def update(self, task_id, advance=1, completed=None, total=None):
        if total is not None:
            self.console.total = total
        self.console.update(completed=completed, advance=advance)

class ResourcePackConverter(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # 基本設置
        self.title(get_text("title", "zh"))
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 設置變數
        self.current_lang = tk.StringVar(value="zh")
        self.current_lang.trace_add("write", self.update_language)
        self.processing = False
        
        # 設置程式目錄
        self.program_dir = os.path.join(os.environ['ProgramFiles'], 'MCPackConverter')
        self.setup_directories()
        
        # 創建臨時工作目錄
        self.temp_dir = tempfile.mkdtemp(prefix="mcpack_")
        os.chmod(self.temp_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        os.makedirs(os.path.join(self.temp_dir, "input"), exist_ok=True)
        
        # 設置輸出目錄
        self.output_dir = os.path.join(self.program_dir, "output")
        
        # 創建主框架
        self.setup_gui()
        
        # 初始化控制台和轉換器
        self.setup_console()

    def setup_directories(self):
        """設置必要的目錄"""
        try:
            # 嘗試創建主程式目錄
            if not os.path.exists(self.program_dir):
                os.makedirs(self.program_dir)
            
            # 創建 input 和 output 目錄
            for dir_name in ['input', 'output']:
                dir_path = os.path.join(self.program_dir, dir_name)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
            
            # 設置目錄權限
            for root, dirs, files in os.walk(self.program_dir):
                for d in dirs:
                    dir_path = os.path.join(root, d)
                    os.chmod(dir_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                for f in files:
                    file_path = os.path.join(root, f)
                    os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                    
        except PermissionError:
            messagebox.showerror(
                "錯誤",
                "無法創建必要的目錄，請以管理員身份運行程式。"
            )
            sys.exit(1)
        except Exception as e:
            messagebox.showerror(
                "錯誤",
                f"設置目錄時發生錯誤：{str(e)}"
            )
            sys.exit(1)

    def setup_gui(self):
        """設置GUI元件"""
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.create_title()
        self.create_language_selection()
        self.create_output_selection()
        self.create_file_list()
        self.create_buttons()
        self.create_progress()
        self.create_status()

    def create_title(self):
        """創建標題"""
        self.title_label = ttk.Label(
            self.main_frame,
            text=get_text("title", self.current_lang.get()),
            font=('TkDefaultFont', 12, 'bold'),
            justify='center'
        )
        self.title_label.pack(pady=10)

    def create_output_directory(self):
        """創建輸出目錄"""
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def create_output_selection(self):
        """創建輸出位置選擇區域"""
        self.output_frame = ttk.LabelFrame(
            self.main_frame,
            text=get_text("output_folder", self.current_lang.get())
        )
        self.output_frame.pack(fill=tk.X, padx=5, pady=5)

        # 顯示當前輸出路徑
        self.output_path_var = tk.StringVar(value=self.output_dir)
        path_label = ttk.Label(
            self.output_frame,
            textvariable=self.output_path_var,
            wraplength=600
        )
        path_label.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        # 變更位置按鈕
        self.change_output_btn = ttk.Button(
            self.output_frame,
            text=get_text("change_output_folder", self.current_lang.get()),
            command=self.change_output_location
        )
        self.change_output_btn.pack(side=tk.RIGHT, padx=5, pady=5)    

    def create_language_selection(self):
        """創建語言選擇區"""
        self.lang_frame = ttk.LabelFrame(
            self.main_frame,
            text=get_text("language_selection", self.current_lang.get())
        )
        self.lang_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Radiobutton(
            self.lang_frame,
            text="中文",
            variable=self.current_lang,
            value="zh"
        ).pack(side=tk.LEFT, padx=20, pady=5)
        
        ttk.Radiobutton(
            self.lang_frame,
            text="English",
            variable=self.current_lang,
            value="en"
        ).pack(side=tk.LEFT, padx=20, pady=5)

    def create_file_list(self):
        """創建檔案列表"""
        self.list_frame = ttk.LabelFrame(
            self.main_frame,
            text=get_text("file_list", self.current_lang.get())
        )
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_list = tk.Listbox(
            self.list_frame,
            yscrollcommand=scrollbar.set
        )
        self.file_list.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.file_list.yview)

    def create_buttons(self):
        """創建按鈕"""
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 左側按鈕
        left_frame = ttk.Frame(btn_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        buttons = [
            ("folder_btn", "choose_folder", self.choose_folder),
            ("zip_btn", "choose_zip", self.choose_zip),
            ("convert_btn", "start_convert", self.start_conversion),
            ("clear_btn", "clear_files", self.clear_files)
        ]
        
        for attr, text_key, command in buttons:
            btn = ttk.Button(
                left_frame,
                text=get_text(text_key, self.current_lang.get()),
                command=command
            )
            btn.pack(side=tk.LEFT, padx=5)
            setattr(self, attr, btn)
        
        # 右側開啟資料夾按鈕
        self.open_output_btn = ttk.Button(
            btn_frame,
            text=get_text("open_output_folder", self.current_lang.get()),
            command=self.open_output_folder
        )
        self.open_output_btn.pack(side=tk.RIGHT, padx=5)

    def change_output_location(self):
        """變更輸出位置"""
        new_dir = filedialog.askdirectory(
            title=get_text("select_output_folder", self.current_lang.get()),
            initialdir=self.output_dir
        )
        if new_dir:
            self.output_dir = new_dir
            self.output_path_var.set(new_dir)

    def open_output_folder(self):
        """開啟輸出資料夾"""
        if sys.platform == "win32":
            os.startfile(self.output_dir)
        elif sys.platform == "darwin":  # macOS
            subprocess.Popen(["open", self.output_dir])
        else:  # Linux
            subprocess.Popen(["xdg-open", self.output_dir])

    def create_progress(self):
        """創建進度條"""
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.main_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

    def create_status(self):
        """創建狀態標籤"""
        self.status_label = ttk.Label(
            self.main_frame,
            text="",
            wraplength=780
        )
        self.status_label.pack(pady=5, fill=tk.X)

    def setup_console(self):
        """設置控制台和轉換器"""
        self.gui_console = GuiConsole(
            self.status_label,
            self.progress_bar,
            self.progress_var
        )
        converter.console = self.gui_console
        converter.CustomProgress = CustomProgress

    def update_language(self, *args):
        """更新介面語言"""
        lang = self.current_lang.get()
        
        self.title(get_text("title", lang))
        self.title_label.config(text=get_text("title", lang))
        self.lang_frame.config(text=get_text("language_selection", lang))
        self.list_frame.config(text=get_text("file_list", lang))
        
        self.folder_btn.config(text=get_text("choose_folder", lang))
        self.zip_btn.config(text=get_text("choose_zip", lang))
        self.convert_btn.config(text=get_text("start_convert", lang))
        self.clear_btn.config(text=get_text("clear_files", lang))

        self.output_frame.config(text=get_text("output_folder", lang))
        self.change_output_btn.config(text=get_text("change_output_folder", lang))
        self.open_output_btn.config(text=get_text("open_output_folder", lang))
        
        converter.CURRENT_LANG = lang

    def set_buttons_state(self, state):
        """設置按鈕狀態"""
        for btn in [self.folder_btn, self.zip_btn, self.convert_btn, self.clear_btn]:
            btn.state([state])

    def handle_remove_readonly(self, func, path, exc):
        """處理唯讀檔案的刪除"""
        excvalue = exc[1]
        if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            func(path)
        else:
            raise excvalue

    def process_files_async(self, input_path, is_zip=False):
        """非同步處理檔案"""
        try:
            input_dir = os.path.join(self.temp_dir, "input")
            if os.path.exists(input_dir):
                shutil.rmtree(input_dir, onerror=self.handle_remove_readonly)
            os.makedirs(input_dir)

            lang = self.current_lang.get()
            if is_zip:
                self.status_label.config(text=get_text("extracting", lang))
                with zipfile.ZipFile(input_path, 'r') as zip_ref:
                    file_list = [f for f in zip_ref.namelist() 
                                if not f.startswith('.git/')]
                    total_files = len(file_list)
                    for i, file in enumerate(file_list, 1):
                        zip_ref.extract(file, input_dir)
                        self.progress_var.set((i / total_files) * 100)
            else:
                self.status_label.config(text=get_text("copying_files", lang))
                total_items = sum([len(files) for root, _, files in os.walk(input_path) 
                                if '.git' not in root])
                processed = 0
                
                for root, _, files in os.walk(input_path):
                    if '.git' in root:
                        continue
                        
                    for file in files:
                        src_path = os.path.join(root, file)
                        rel_path = os.path.relpath(src_path, input_path)
                        dst_path = os.path.join(input_dir, rel_path)
                        
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                        
                        processed += 1
                        self.progress_var.set((processed / total_items) * 100)

            self.update_file_list()
            self.status_label.config(text="")
            self.progress_var.set(0)

        except Exception as e:
            self.after(0, messagebox.showerror, 
                        get_text("error", self.current_lang.get()), 
                        str(e))
        finally:
            self.processing = False
            self.after(0, self.set_buttons_state, '!disabled')

    def update_file_list(self):
        """更新檔案列表"""
        self.file_list.delete(0, tk.END)
        input_dir = os.path.join(self.temp_dir, "input")
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith('.json'):
                    rel_path = os.path.relpath(os.path.join(root, file), input_dir)
                    self.file_list.insert(tk.END, rel_path)

    def choose_folder(self):
        """選擇資料夾"""
        if self.processing:
            return
        
        folder = filedialog.askdirectory(
            title=get_text("select_folder", self.current_lang.get())
        )
        if folder:
            self.processing = True
            self.set_buttons_state('disabled')
            threading.Thread(
                target=self.process_files_async,
                args=(folder, False)
            ).start()

    def choose_zip(self):
        """選擇ZIP檔案"""
        if self.processing:
            return
            
        zip_file = filedialog.askopenfilename(
            title=get_text("select_zip", self.current_lang.get()),
            filetypes=[("ZIP files", "*.zip")]
        )
        if zip_file:
            self.processing = True
            self.set_buttons_state('disabled')
            threading.Thread(
                target=self.process_files_async,
                args=(zip_file, True)
            ).start()

    def clear_files(self):
        """清除檔案"""
        self.file_list.delete(0, tk.END)
        input_dir = os.path.join(self.temp_dir, "input")
        if os.path.exists(input_dir):
            shutil.rmtree(input_dir, onerror=self.handle_remove_readonly)
        os.makedirs(input_dir)
        self.progress_var.set(0)
        self.status_label.config(text="")

    def start_conversion(self):
        """開始轉換"""
        lang = self.current_lang.get()
        if self.file_list.size() == 0:
            messagebox.showwarning(
                get_text("warning", lang),
                get_text("select_files_first", lang)
            )
            return
        
        if self.processing:
            return
            
        self.processing = True
        self.set_buttons_state('disabled')
        threading.Thread(target=self.convert_files).start()

    def convert_files(self):
        """執行轉換"""
        try:
            lang = self.current_lang.get()
            original_cwd = os.getcwd()
            temp_output_dir = None

            # 設置語言
            converter.CURRENT_LANG = self.current_lang.get()
            
            # 創建時間戳記
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_zip = f"converted_{timestamp}.zip"
            output_path = os.path.join(self.output_dir, output_zip)  # 使用設定的輸出目錄
            
            # 準備目錄
            temp_input_dir = os.path.join(self.temp_dir, "input")
            temp_output_dir = os.path.join(self.temp_dir, "temp_output")
            
            # 設置工作目錄為臨時目錄
            os.chdir(self.temp_dir)
            
            # 確保輸出目錄存在
            if not os.path.exists(temp_output_dir):
                os.makedirs(temp_output_dir)
            
            try:
                # 執行轉換
                processed_files = converter.process_directory(temp_input_dir, temp_output_dir)
                
                # 調整資料夾結構
                converter.adjust_folder_structure(temp_output_dir)
                
                # 建立 ZIP
                zip_temp_path = os.path.join(self.temp_dir, output_zip)
                converter.create_zip(temp_output_dir, zip_temp_path)
                
                # 確保輸出目錄存在
                os.makedirs(self.output_dir, exist_ok=True)
                
                # 如果目標檔案已存在，先刪除
                if os.path.exists(output_path):
                    os.remove(output_path)
                
                # 移動 ZIP 到最終位置
                if os.path.exists(zip_temp_path):
                    shutil.move(zip_temp_path, output_path)
                    
                    self.after(0, messagebox.showinfo,
                        get_text("complete", lang),
                        get_text("conversion_complete", lang).format(output_zip)
                    )
                else:
                    raise Exception(get_text("conversion_failed", lang).format(
                        "未能生成輸出檔案" if lang == "zh" else "Failed to generate output file"
                    ))
                
            finally:
                # 恢復原始工作目錄
                os.chdir(original_cwd)
            
        except Exception as e:
            self.after(0, messagebox.showerror, 
                        get_text("error", lang), 
                        str(e))
            
        finally:
            # 清理並重置
            self.processing = False
            self.progress_var.set(0)
            self.status_label.config(text="")
            self.after(0, self.set_buttons_state, '!disabled')
            
            # 清理臨時輸出目錄
            if temp_output_dir and os.path.exists(temp_output_dir):
                try:
                    shutil.rmtree(temp_output_dir, onerror=self.handle_remove_readonly)
                except Exception:
                    pass

    def on_closing(self):
        """關閉視窗時的處理"""
        lang = self.current_lang.get()
        if self.processing:
            response = messagebox.askokcancel(
                get_text("confirm_exit", lang),
                get_text("confirm_exit_processing", lang),
                icon="warning"
            )
        else:
            response = messagebox.askokcancel(
                get_text("confirm_exit", lang),
                get_text("confirm_exit_normal", lang),
                icon="question"
            )
        
        if response:
            if os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir, onerror=self.handle_remove_readonly)
                except Exception:
                    pass
            self.quit()

def main():
    """主程式"""
    try:
        if sys.platform.startswith('win'):
            os.system('chcp 65001')
        
        app = ResourcePackConverter()
        app.mainloop()
    except Exception as e:
        # 顯示錯誤訊息
        import traceback
        error_message = f"發生錯誤:\n{str(e)}\n\n詳細資訊:\n{traceback.format_exc()}"
        if 'app' in locals() and hasattr(app, 'destroy'):
            messagebox.showerror("錯誤", error_message)
            app.destroy()
        else:
            # 如果 GUI 尚未創建，使用控制台輸出
            print(error_message)
            input("按 Enter 鍵關閉程式...")
        sys.exit(1)

if __name__ == "__main__":
    main()