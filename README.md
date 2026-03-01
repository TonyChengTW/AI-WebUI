> **版本: v0.4.3 作者: Tony Cheng (tony.pig@gmail.com) 
> © Tony 數位工作室 本程式著作權及其他智慧財產權，全數開源GPL授權使用。**

# 💬 AI-WebUI 小幫手

![DeepSeek & Llama Chat](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Ollama Integration](https://img.shields.io/badge/Ollama-Integrated-007bff?style=for-the-badge&logo=ollama&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker_Compose-Ready-0db7ed?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg?style=for-the-badge)

這是一個專門為自己弄出來的 Web 介面。原本只是想方便做 Vibe Coding，沒想到最後連自動畫圖、代碼診斷跟檔案管理都一併處理了...。

---

## ✨ 主要功能
- **Ollama 模型整合**: 輕鬆連接至本地的 Ollama 服務，與預裝好的各種大模型玩耍。
- **使用者認證**: 簡單的帳密登入機制，支援 Cookie 記憶，不用每次都填。
- **紀錄儲存**: 每個使用者都有獨立的對話紀錄，換個電腦登入也還在。
- **系統指令 (Persona)**: 自由設定 AI 是要變技術大神還是幽默小編，存檔後自動記憶。
- **檔案附件 (強項)**: 支援上傳 `PDF`, `DOCX`, `CSV`, `XLSX`, `PY`, `JSON`, `YAML` 等超多格式，AI 會直接看過內容後再回覆。
- **繁體中文優化**: 強制 AI 用台灣繁體中文，不會在那邊「親、打印、屏幕」。
- **思考過程顯示**: 只要模型支援，AI 的「私密碎碎念 (Thought)」都會透明化給你看。

---

### 🚀 這幾版我強化的東西

- **自動歸檔 (產物不失蹤)**
  點擊「執行圖表」後的 Python 腳本跟產生的圖片，通通會自動丟進 `scripts/outputs/`。下班回家想用 SSH 回去看昨天 AI 畫了什麼？直接進這資料夾就對了。
  
- **代碼自動打磨 (Syntax Aegis)**
  AI 有時會寫錯語法。我加了一個自動修正器，還會自動攔截那些會讓 Docker 畫面卡死的 `plt.show()`。

- **強韌連線 (不再死機)**
  大模型載入很慢？我把超時拉到了 5 分鐘。要是記憶體爆了 (OOM)，它會直接在網頁上講明，不用再去翻 log。

- **硬核登出**
  解決了那個點了登出卻又自動登入的縮頭 Bug。

---

## ⚙️ 設定使用者帳密
此應用程式使用 Streamlit 的 `st.secrets` 來管理。請在專案根目錄下，創建 `.streamlit` 資料夾並建立 `secrets.toml`：

```toml
# .streamlit/secrets.toml
[passwords]
admin = "你的管理員密碼"
user1 = "其他使用者密碼"
```

---

## � 下載 Ollama 模型 (可選)
當 Ollama 服務跑起來後，你可以用終端機下載你要的模型（推薦）：

```bash
docker exec -it ollama ollama pull llama3.2:3b
docker exec -it ollama ollama pull qwen2.5-vl:3b
docker exec -it ollama ollama pull deepseek-v2:lite
```

---

## 🎮 使用方式
1. **訪問應用**: 跑起 Docker 後，去瀏覽器開 `http://localhost:8501`。
2. **登入**: 用你在 `secrets.toml` 設的帳密進場。
3. **聊天**: 
   - 左側選模型、設風格。
   - 下方輸入訊息。
   - 點「📎」上傳文件讓 AI 當參考書。
4. **管理功能**: 以 `admin` 登入時，側邊欄可以手動隱藏你不想看到的模型。

---

## 📂 專案結構
```text
.
├── .streamlit/             # 配置資料夾
│   └── secrets.toml        # 使用者帳密存檔
├── app.py                  # 萬能主程式
├── Dockerfile              # 構建 WebUI 的藍圖
├── docker-compose.yml      # 一鍵啟動的指揮官 (含 WebUI & Ollama)
├── history/                # 對話紀錄存檔資料夾
├── scripts/outputs/        # AI 畫的圖與產生的腳本
└── README.md               # 你現在看的這份
```

> **請注意**: 本專案的 `app.py` 與 `Dockerfile` 均位於根目錄，確保 `docker-compose.yml` 能夠直接構建。

---

> **版本: v0.4.3 作者: Tony Cheng (tony.pig@gmail.com) 
> © Tony 數位工作室 本程式著作權及其他智慧財產權，全數開源GPL授權使用。**