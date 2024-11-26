# Minecraft-ResourcePack-Migrator 1.14 ~ 1.21.4+

一個專門用於將 Minecraft 資源包（Resource Pack）從舊版本（1.14）轉換至 1.21.4+ 版本的工具。
這個工具主要處理物品模型的 JSON 格式轉換，協助創作者快速更新他們的資源包。

## 主要功能

- 自動轉換舊版本的物品模型 JSON 格式至 1.21+ 新格式
- 自動調整資料夾結構（`assets/minecraft/models/item/*` → `assets/minecraft/items/*`）
- 智慧處理 `minecraft:item/` 和 `item/` 的路徑前綴
- 批次處理整個資源包
- 即時顯示轉換進度
- 自動打包為可直接使用的資源包

## 支援版本

- 輸入：Minecraft 1.14 ~ 1.21.3 的資源包
- 輸出：Minecraft 1.21.4+ 相容格式

## 快速開始

1. 下載此工具：
```bash
git clone https://github.com/BrilliantTeam/Minecraft-ResourcePack-Migrator
cd minecraft-resourcepack-migrator
```

2. 準備你的資源包：
```
resourcepack-migrator/
    ├── run.py           # 執行腳本
    ├── converter.py     # 轉換程式
    └── input/           # 放入你的資源包內容
        └── assets/
            └── minecraft/
                ├── models/
                │   └── item/   # 物品模型檔案
                ├── textures/   # 材質檔案
                └── ...        # 其他資源包檔案
```

3. 執行轉換：
```bash
python run.py
```

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

新版本格式（1.21.4+）：
```json
{
  "model": {
    "type": "select",
    "property": "custom_model_data",
    "fallback": {
      "type": "model",
      "model": "item/stick"
    },
    "cases": [
      {
        "when": "19002",
        "model": {
          "type": "model",
          "model": "custom_items/cat_hat/cat_hat_black"
        }
      }
    ]
  }
}
```

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
   - 此 ZIP 檔案可直接作為 Minecraft 1.21+ 的資源包使用

## 轉換規則

1. JSON 格式更新：
   - 更新為 1.21+ 的新物品模型格式
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