README LANGUAGES [ [English](README.md) | [**中文**](README-中文.md) ]
# Minecraft-ResourcePack-Migrator 1.14 ~ 1.21.4+

一個專門用於將 Minecraft 資源包（Resource Pack）從舊版本（1.14）轉換至 1.21.4+ 版本的工具。
這個工具主要處理物品模型的 JSON 格式轉換，協助創作者快速更新他們的資源包。

## 主要功能

- 自動轉換舊版本的物品模型 JSON 格式至 1.21.4+ 新格式
- 自動調整資料夾結構（`assets/minecraft/models/item/*` → `assets/minecraft/items/*`）
- 智慧處理 `minecraft:item/` 和 `item/` 的路徑前綴
- 批次處理整個資源包
- 即時顯示轉換進度
- 自動打包為可直接使用的資源包
- 圖形使用者介面，操作簡單

## 支援版本

- 輸入：Minecraft 1.14 ~ 1.21.3 的資源包
- 輸出：Minecraft 1.21.4+ 相容格式

## 安裝與使用

### 方法一：使用執行檔（推薦）
1. 從 [Releases](https://github.com/BrilliantTeam/Minecraft-ResourcePack-Migrator/releases) 頁面下載最新版本
2. 執行 MCPackConverter.exe
3. 選擇你偏好的語言（中文/English）
4. 使用圖形介面：
   - 選擇資料夾或 ZIP 檔案
   - 點擊「開始轉換」
   - 在輸出資料夾中找到轉換後的資源包

### 方法二：使用原始碼
1. 複製專案：
```bash
git clone https://github.com/BrilliantTeam/Minecraft-ResourcePack-Migrator
cd minecraft-resourcepack-migrator
```

2. 安裝需求套件：
```bash
pip install rich
```

3. 執行程式：
   - 圖形介面版本：`python gui_app.py`
   - 命令列版本：`python run.py`

### 方法三：自行建構執行檔
1. 複製專案：
```bash
git clone https://github.com/BrilliantTeam/Minecraft-ResourcePack-Migrator
cd minecraft-resourcepack-migrator
```

2. 安裝必要套件：
```bash
pip install pyinstaller rich
```

3. 執行建構腳本：
```bash
python build.py
```

4. 尋找執行檔：
   - 建構完成的執行檔會在 `dist` 資料夾中
   - 可以直接執行 `MCPackConverter.exe`

注意：建構執行檔需要系統管理員權限，這是因為檔案路徑設定的需求。

## 格式轉換示例

舊版本格式（1.14 ~ 1.21.3）：
```json
{
    "parent": "item/handheld",
    "textures": {
        "layer0": "item/stick"
    },
    "overrides": [
        {"predicate": {"custom_model_data": 19002}, "model":"custom_items/cat_hat/cat_hat_black"}
    ]
}
```
` /give @s minecraft:stick{CustomModelData:19002} `

新版本格式（1.21.4+）：
```json
{
  "model": {
    "type": "range_dispatch",
    "property": "custom_model_data",
    "fallback": {
      "type": "model",
      "model": "item/stick"
    },
    "entries": [
      {
        "threshold": 19002,
        "model": {
          "type": "model",
          "model": "custom_items/cat_hat/cat_hat_black"
        }
      }
    ]
  }
}
```
` /give @s minecraft:stick[custom_model_data={floats:[19002]}] `

## 使用需求

- Python 3.6 或更新版本
- pip（Python 套件管理器）

自動安裝的套件：
- tqdm（用於顯示進度條）

## 詳細使用步驟

1. 準備資源包：
   - 將完整的資源包內容放入 `input` 資料夾
   - 確保保持原始的資料夾結構

2. 執行轉換：
   - Windows：雙擊 `run.py` 或使用命令 `python run.py`
   - Mac/Linux：在終端機執行 `python3 run.py`

3. 檢視結果：
   - 程式會生成一個時間戳記命名的 ZIP 檔案（例：`converted_20240326_123456.zip`）
   - 此 ZIP 檔案可直接作為 Minecraft 1.21.4+ 的資源包使用

## 轉換規則

1. JSON 格式更新：
   - 更新為 1.21.4+ 的新物品模型格式
   - 保留所有自訂模型資料（custom_model_data）

2. 路徑處理：
   - `minecraft:item/*` 路徑會保持其前綴
   - `item/*` 路徑保持原有格式
   - 自動調整物品模型的存放位置

3. 資料夾結構調整：
   - 將 `models/item/*` 中的檔案移動至 `items/*`
   - 保留其他資料夾的原始結構

## 注意事項

1. 轉換前請務必備份你的原始資源包
2. 確保輸入的資源包結構正確
3. 轉換後請在遊戲中測試所有自訂物品模型
4. 如果發現任何問題，請檢查輸出的錯誤訊息

## 問題排解

如果遇到問題，請檢查：
1. 輸入資料夾結構是否正確
2. JSON 檔案格式是否有效
3. Python 版本是否符合要求
4. 是否有足夠的檔案讀寫權限

## 貢獻

歡迎提交 Issue 或 Pull Request 來協助改善這個工具。主要的貢獻方向：
- 支援更多的模型格式
- 改善轉換效率
- 擴充錯誤處理
- 提升使用者體驗

## 授權

GNU General Public License v3.0