# AI 小幫手 (Ollama Web UI)

![DeepSeek & Llama Chat](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Ollama Integration|199](https://img.shields.io/badge/Ollama-Integrated-007bff?style=for-the-badge&logo=ollama&logoColor=white)
![Docker Compose](https://img.shields.io/badge/Docker_Compose-Ready-0db7ed?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-GPLv3-blue.svg?style=for-the-badge)

一個基於 Streamlit 開發的 AI 聊天介面，專為整合 Ollama 本地語言模型設計。此應用程式提供使用者友善的介面，支援多模型選擇、聊天歷史記錄、系統指令自訂、檔案附件功能，並特別強調台灣繁體中文的輸出。

![[Pasted image 20260228183400.png]]

![[output.webp]]
## ✨ 主要功能

*   **Ollama 模型整合**: 輕鬆連接至本地的 Ollama 服務，與各種大語言模型進行互動。
*   **使用者認證**: 簡單的使用者帳號密碼登入機制，支援 Cookie 記憶。
*   **聊天歷史記錄**: 為每個使用者獨立儲存和載入聊天對話記錄。
*   **自訂系統指令**: 自由設定 AI 的行為與回答風格，並持久化保存。
*   **模型選擇與管理**: 列出可用的 Ollama 模型，管理員可設定隱藏特定模型。
*   **檔案附件功能**: 支援上傳多種檔案類型 (TXT, MD, PY, CFG, JSON, YAML, YML, PDF, DOCX, CSV, XLSX, JPG, JPEG, PNG)，AI 可根據檔案內容進行回覆。
*   **繁體中文優化**: 強調使用「台灣繁體中文」進行回答，並力求貼近台灣當地語氣與慣用語。
*   **思考過程顯示**: AI 回覆時會顯示其思考過程，提升互動透明度 (需模型支援)。
## 🚀 快速開始

### 環境需求

在啟動此專案之前，請確保您的系統已安裝以下軟體：

*   **Docker**: [安裝教學](https://docs.docker.com/get-docker/)
*   **Docker Compose**: 通常隨 Docker Desktop 一同安裝。

### 安裝與設定

1.  **複製儲存庫**:
    ```bash
    git clone https://github.com/YourUsername/your-repo-name.git # 將 YourUsername/your-repo-name 替換為實際的 GitHub 路徑
    cd your-repo-name
    ```

2.  **設定使用者帳密**:
    此應用程式使用 Streamlit 的 `st.secrets` 來管理使用者帳號和密碼。
    在專案根目錄下，創建一個 `.streamlit` 資料夾，並在其中創建 `secrets.toml` 檔案：

    ```
    # .streamlit/secrets.toml
    [passwords]
    admin = "your_admin_password"
    user1 = "your_user1_password"
    # 可以添加更多使用者
    ```
    **注意**: 這是基本認證，不適用於安全性要求高的場景。請妥善保管您的密碼。

3.  **構建並啟動服務**:
    此專案使用 Docker Compose 啟動 Ollama 服務和 Streamlit Web UI。

    ```bash
    docker-compose up --build -d
    ```
    這將會：
    *   下載 `ollama/ollama:latest` 映像檔。
    *   構建 `ai-webui` 的 Docker 映像檔 (基於您提供的 `Dockerfile`，假設它在 `ai_webui` 資料夾內)。
    *   啟動兩個容器：`ollama` 和 `ai_webui`。

4.  **下載 Ollama 模型 (可選)**:
    當 Ollama 服務啟動後，您可以透過兩種方式下載模型：

    *   **透過 Web UI 提示**: 應用程式會提示您哪些模型尚未下載。
    *   **透過終端機 (推薦)**: 進入 Ollama 容器，手動下載模型。
        ```bash
        docker exec -it ollama ollama pull llama3
        docker exec -it ollama ollama pull deepseek-coder
        # 您可以下載任何您想要的模型
        ```
    請注意，模型下載可能需要一些時間和大量儲存空間。

## 🖥️ 使用方式

1.  **訪問應用程式**:
    服務啟動後，打開您的網路瀏覽器，訪問：
    `http://localhost:8501`

2.  **登入**:
    使用您在 `.streamlit/secrets.toml` 中設定的帳號和密碼登入。

3.  **開始聊天**:
    *   在左側邊欄選擇您想要使用的 Ollama 模型。
    *   在左側邊欄的「系統指令」區域設定 AI 的行為。
    *   在下方的輸入框中輸入您的訊息。
    *   您可以點擊「📎 附加檔案」來上傳文件，其內容將被包含在您的提問中。

4.  **管理員功能**:
    如果以 `admin` 帳號登入，在左側邊欄會出現「管理員模型控制」區塊，您可以在此隱藏/顯示特定的模型。

## 📂 專案結構

```
.
├── .streamlit/             # Streamlit 應用程式的配置資料夾
│   └── secrets.toml        # 存放使用者帳號與密碼
├── ai_webui/               # Streamlit Web UI 應用程式的根目錄
│   ├── app.py              # Streamlit 應用程式主程式
│   └── Dockerfile          # 用於構建 ai-webui 服務的 Dockerfile
├── docker-compose.yml      # Docker Compose 設定檔，定義服務、網路和儲存卷
└── README.md               # 本說明文件
```

**請注意**: `Dockerfile` 應存在於 `ai_webui/` 目錄中，以便 `docker-compose.yml` 可以成功構建 `ai-webui` 服務。如果沒有，您需要自行創建一個，通常包含 Python 環境設定和應用程式啟動指令。

## 🤝 貢獻

歡迎任何形式的貢獻！如果您有任何建議、錯誤報告或功能請求，請隨時提交 Issue 或 Pull Request。

## 📄 授權

此專案根據 GNU GPL v3 授權發布。詳情請參閱 [LICENSE](LICENSE) 檔案。

---

**版本**: `v0.4.3`
**作者**: Tony Cheng (tony.pig@gmail.com)
© Tony 數位工作室
本程式著作權及其他智慧財產權，全數開源GPL授權使用。