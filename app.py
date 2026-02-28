import os
import time
import datetime
import extra_streamlit_components as stx
import streamlit as st
import requests
import json
import uuid
import re

# --- Helper for Rendering Content with Mermaid ---
def render_content(content):
    """
    Renders markdown content with Mermaid support.
    """
    if "```mermaid" not in content:
        st.markdown(content)
        return

    # Split content by mermaid blocks
    pattern = r"```mermaid\b(.*?)\n?```"
    parts = re.split(pattern, content, flags=re.DOTALL)
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            # Markdown part
            if part.strip():
                st.markdown(part)
        else:
            # Mermaid part
            mermaid_code = part.strip()
            if mermaid_code:
                # Use a unique key for each component
                st.components.v1.html(
                    f"""
                    <div class="mermaid" style="display: flex; justify-content: center;">
                        {mermaid_code}
                    </div>
                    <script type="module">
                        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                        mermaid.initialize({{ 
                            startOnLoad: true,
                            theme: 'default',
                            securityLevel: 'loose',
                        }});
                    </script>
                    """,
                    height=400,
                    scrolling=True
                )


# --- Configuration & Metadata ---
VERSION = "v0.4.3"
AUTHOR = "Tony Cheng (tony.pig@gmail.com)"
DEFAULT_SYSTEM_PROMPT = "你是一個專業助手。請務必使用 **繁體中文** ，以及**台灣當地**的語調和慣用語來進行回答，愈接地氣愈好。絕對禁用簡體字。此外，當你需要解釋流程、結構或時序時，請盡量使用 Mermaid 語法產生圖表（例如：graph TD, sequenceDiagram 等），並將其置於 ```mermaid 區塊中。"

st.set_page_config(page_title="DeepSeek & Llama Chat", page_icon="🤖", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "stop_gen" not in st.session_state:
    st.session_state.stop_gen = False
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = DEFAULT_SYSTEM_PROMPT
if "pending_final_prompt" not in st.session_state:
    st.session_state.pending_final_prompt = None

# --- History Persistence ---
def get_user_history_path():
    if "current_user" in st.session_state:
        return f"history_{st.session_state['current_user']}.json"
    return None

def load_history():
    path = get_user_history_path()
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(messages):
    path = get_user_history_path()
    if path:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"儲存紀錄失敗: {e}")

# --- Authentication Logic (with Cookie Persistence) ---
def get_cookie_manager():
    # 注意：CookieManager 內部包含 widget 命令，不能使用 @st.cache_resource 裝飾
    return stx.CookieManager()

def check_password():
    """Returns `True` if the user had the correct password."""
    cookie_manager = get_cookie_manager()
    
    # 嘗試從 Cookie 恢復 Session 與 系統指令
    if "password_correct" not in st.session_state:
        saved_user = cookie_manager.get("current_user")
        if saved_user:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = saved_user
            st.session_state.messages = load_history()
            
            # 同時恢復系統指令
            saved_prompt = cookie_manager.get("system_prompt")
            if saved_prompt:
                st.session_state.system_prompt = saved_prompt

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        username = st.session_state["username_input"]
        password = st.session_state["password_input"]
        if username in st.secrets["passwords"] and \
           password == st.secrets["passwords"][username]:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = username
            # 存入 Cookie (有效期 7 天)
            cookie_manager.set("current_user", username, expires_at=datetime.datetime.now() + datetime.timedelta(days=7))
            del st.session_state["password_input"]
            del st.session_state["username_input"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.title("🔐 AI 系統登入")
        st.text_input("使用者帳號", key="username_input")
        st.text_input("密碼", type="password", key="password_input")
        if st.button("登入"):
            password_entered()
            if not st.session_state.get("password_correct", False):
                st.error("😕 帳號或密碼錯誤")
            else:
                # 登入成功後立即加載歷史紀錄
                st.session_state.messages = load_history()
                st.rerun()
        
        st.divider()
        st.caption(f"系統版本: {VERSION} | 作者: {AUTHOR}")
        return False
    return True

# If not authenticated, stop here
if not check_password():
    st.stop()
# 此處不再重複加載，由登入邏輯和初始化確保
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Model Visibility Management ---
HIDDEN_MODELS_PATH = "hidden_models.json"

def load_hidden_models():
    if os.path.exists(HIDDEN_MODELS_PATH):
        try:
            with open(HIDDEN_MODELS_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_hidden_models(hidden_set):
    try:
        with open(HIDDEN_MODELS_PATH, "w", encoding="utf-8") as f:
            json.dump(list(hidden_set), f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"儲存隱藏模型清單失敗: {e}")

if "hidden_models" not in st.session_state:
    st.session_state.hidden_models = load_hidden_models()

# --- Custom CSS for Premium Look ---
st.markdown("""
<style>
    .stChatMessage {
        border-radius: 15px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eee;
    }
    .stChatInputContainer {
        padding-bottom: 2rem;
    }
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Sidebar for configuration ---
with st.sidebar:
    st.write(f"👤 當前使用者: **{st.session_state['current_user']}**")
    
    default_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_url = st.text_input("Ollama API 網址", value=default_url).strip().rstrip("/")
    
    # Try to fetch models from Ollama
    available_models = []
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=10)
        if response.status_code == 200:
            models_data = response.json().get('models', [])
            available_models = [m['name'] for m in models_data]
    except Exception:
        pass

    recommended = ["qwen2.5:3b", "deepseek-r1:1.5b", "llama3.2:3b"]
    full_model_options = list(set(available_models + recommended))
    
    # --- Admin Model Management ---
    if st.session_state["current_user"] == "admin":
        st.divider()
        st.write("🔧 **管理員模型控制**")
        to_hide = st.multiselect(
            "選擇要隱藏的模型",
            options=sorted(full_model_options),
            default=[m for m in st.session_state.hidden_models if m in full_model_options]
        )
        if st.button("更新隱藏清單"):
            st.session_state.hidden_models = set(to_hide)
            save_hidden_models(st.session_state.hidden_models)
            st.success("已更新清單")
            st.rerun()

    # Filter out hidden models (for non-admins or as a general rule)
    visible_models = [m for m in full_model_options if m not in st.session_state.hidden_models]
    if not visible_models: visible_models = full_model_options # Fallback

    # 直接使用原始模型名稱，包含 :latest 標籤
    display_names = sorted(visible_models)
    
    # 智慧預設值：優先選擇已經下載好的模型
    default_idx = 0
    
    found_default = False
    for i, name in enumerate(display_names):
        if name in available_models:
            if "qwen" in name.lower():
                default_idx = i
                found_default = True
                break
            elif not found_default: # 第一個找到的已安裝模型作為備選
                default_idx = i
                found_default = True
                
    selected_model = st.selectbox("選擇模型", options=display_names, index=default_idx)
    
    if selected_model not in available_models:
        st.warning(f"⚠️ 模型 `{selected_model}` 尚未下載，對話時可能會失敗。")
    
    st.info(f"當前選定: **{selected_model}**")

    st.divider()
    st.write("⚙️ **系統指令 (System Prompt)**")
    new_system_prompt = st.text_area(
        "設定 AI 的行為指令", 
        value=st.session_state.system_prompt,
        placeholder="例如：你是一個資深工程師，請用簡潔的語言回答...",
        help="這會影響 AI 的回答風格與語言偏好。"
    )
    if new_system_prompt != st.session_state.system_prompt:
        st.session_state.system_prompt = new_system_prompt
        # 存入 Cookie (有效期 7 天)
        cookie_manager = get_cookie_manager()
        cookie_manager.set("system_prompt", new_system_prompt, expires_at=datetime.datetime.now() + datetime.timedelta(days=7))
        st.success("指令已儲存並持久化")

    # --- 語系汙染提示 ---
    has_simplified = False
    for msg in st.session_state.messages[-3:]: # 檢查最近 3 則
        if msg["role"] == "assistant" and any(c in msg["content"] for c in "这说还国为会"):
            has_simplified = True
            break
    if has_simplified:
        st.warning("⚠️ 偵測到 AI 曾使用簡體回覆過。由於對話紀錄會影響 AI 的慣性，建議點擊下方「清除對話紀錄」再重試，以獲得最佳繁體效果。")


    if st.button("清除對話紀錄"):
        st.session_state.messages = []
        save_history([])
        st.rerun()
    
    if st.button("登出"):
        cookie_manager = get_cookie_manager()
        cookie_manager.delete("current_user")
        cookie_manager.delete("system_prompt")
        st.session_state["password_correct"] = False
        st.session_state["current_user"] = None
        st.rerun()

    st.divider()
    st.caption(f"🛠️ 系統版本: {VERSION}")
    st.caption(f"👨‍💻 作者: {AUTHOR}")
    st.caption("⚖️ Licensed under GNU GPL v3")

st.title("💬 Tony的AI小幫手")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("thought"):
            with st.expander("💭 思考過程 (已存檔)", expanded=False):
                render_content(message["thought"])
        render_content(message["content"])

# Function to query Ollama (Streaming)
def generate_response(messages):
    payload = {"model": selected_model, "messages": messages, "stream": True}
    base_url = ollama_url.strip().rstrip("/")
    
    try:
        # 設定非常長的 timeout (連線 60 秒，讀取 86400 秒即 24 小時) 避免 Session 靜默斷線
        with requests.post(f"{base_url}/api/chat", json=payload, stream=True, timeout=(60, 86400)) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if st.session_state.get("stop_gen", False):
                    break
                if line:
                    chunk = json.loads(line)
                    if "message" in chunk:
                        yield chunk["message"].get("content", "")
                    if chunk.get("done"): break
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404:
            yield f"\n\n⚠️ **模型未找到 (404)**\n\n您選擇的模型 `{selected_model}` 尚未下載到此 Ollama 伺服器中。\n\n**解決方案：**\n1. 在網頁左側選擇已安裝的模型 (如 `llama3.2:latest`)。\n2. 或在終端機執行 `docker exec -it ollama ollama run {selected_model}` 來下載它。"
        else:
            yield f"\n\n⚠️ 連線錯誤: HTTP {err.response.status_code} - 請確認 Ollama 服務路徑是否正確。"
    except Exception as e:
        yield f"\n\n⚠️ 系統錯誤: {str(e)}"


# --- Assistant Response Generation (if generating) ---
if st.session_state.is_generating and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        # 建立思考過程與回答內容的容器
        thought_container = st.expander("💭 思考過程", expanded=True)
        response_placeholder = st.empty()
        
        with st.status("Tony 的 AI 正在努力中...", expanded=False) as status:
            full_response = ""
            thought_content = ""
            actual_response = ""
            is_thinking = False
            has_started = False
            
            # 使用 pending_final_prompt 作為最新的使用者訊息
            latest_content = st.session_state.pending_final_prompt if st.session_state.pending_final_prompt else st.session_state.messages[-1]["content"]
            
            # 建立帶有 System Prompt 的上下文
            temp_messages = []
            if st.session_state.system_prompt:
                temp_messages.append({"role": "system", "content": st.session_state.system_prompt})
            
            # 加入歷史紀錄備份 (除了最後一則 user 訊息，因為我們要換成含檔案內容的版本)
            for msg in st.session_state.messages[:-1]:
                temp_messages.append({"role": msg["role"], "content": msg["content"]})
            
            temp_messages.append({"role": "user", "content": latest_content})
            
            for chunk in generate_response(temp_messages):
                if st.session_state.get("stop_gen", False):
                    actual_response += "\n\n[已手動停止生成]"
                    break
                
                full_response += chunk
                
                # --- 核心邏輯：解析 <think> 標籤 ---
                if "<think>" in full_response:
                    if "</think>" in full_response:
                        is_thinking = False
                        parts = full_response.split("</think>")
                        thought_content = parts[0].replace("<think>", "").strip()
                        actual_response = parts[1].strip()
                    else:
                        is_thinking = True
                        thought_content = full_response.replace("<think>", "").strip()
                else:
                    actual_response = full_response

                # --- 動態渲染 UI ---
                if thought_content:
                    thought_container.markdown(thought_content)
                
                if actual_response:
                    if is_thinking == False and thought_content:
                        thought_container.update(label="💭 思考完成 (點擊展開)", expanded=False)
                    response_placeholder.markdown(actual_response + "▌")
                
                if not has_started and (thought_content or actual_response):
                    status.update(label="正在生成回覆...", state="running", expanded=False)
                    has_started = True
            
            status.update(label="回覆完成" if not st.session_state.get("stop_gen", False) else "已停止", state="complete")
            with response_placeholder.container():
                render_content(actual_response)
            
            # 儲存對話
            st.session_state.messages.append({
                "role": "assistant", 
                "content": actual_response,
                "thought": thought_content if thought_content else None
            })
            save_history(st.session_state.messages)
            
            # 重置狀態
            st.session_state.is_generating = False
            st.session_state.stop_gen = False
            st.session_state.pending_final_prompt = None
            st.rerun()

# --- File Uploader area ---
st.divider()
with st.expander("📎 附加檔案 (支援 Python, Config, PDF, 圖片等)", expanded=True):
    uploaded_file = st.file_uploader(
        "上傳檔案區", 
        type=["txt", "md", "py", "cfg", "json", "yaml", "yml", "pdf", "docx", "csv", "xlsx", "jpg", "jpeg", "png"],
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        if "file_content" not in st.session_state or st.session_state.get("last_uploaded_file") != uploaded_file.name:
            with st.spinner(f"正在分析 {uploaded_file.name}..."):
                file_text = ""
                text_extensions = [".txt", ".md", ".py", ".cfg", ".json", ".yaml", ".yml"]
                is_text = any(uploaded_file.name.lower().endswith(ext) for ext in text_extensions)
                
                try:
                    if is_text or uploaded_file.type == "text/plain":
                        file_text = uploaded_file.read().decode("utf-8")
                    elif uploaded_file.type == "application/pdf":
                        import PyPDF2
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        for page in pdf_reader.pages:
                            text = page.extract_text()
                            if text: file_text += text + "\n"
                    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        import docx
                        doc = docx.Document(uploaded_file)
                        file_text = "\n".join([para.text for para in doc.paragraphs])
                    elif "image/" in uploaded_file.type:
                        file_text = f"[已上傳圖片檔案: {uploaded_file.name}]"
                    
                    st.session_state["file_content"] = file_text
                    st.session_state["last_uploaded_file"] = uploaded_file.name
                    st.success(f"📌 檔案【{uploaded_file.name}】讀取成功！", icon="✅")
                except Exception as e:
                    st.error(f"讀取錯誤: {e}")

# --- Chat Input area ---
if st.session_state.is_generating:
    if st.button("🛑 停止生成回覆", use_container_width=True):
        st.session_state.stop_gen = True
        st.rerun()
else:
    if prompt := st.chat_input("傳送訊息給 AI..."):
        st.session_state.stop_gen = False
        st.session_state.is_generating = True
        
        # 最強力的語言鎖定：直接放在問題最後面
        lang_suffix = "\n\n(重要指令：請使用『台灣繁體中文』回答，必須使用台灣常用的詞彙與語氣，不可使用簡體字。)"
        final_prompt = prompt + lang_suffix
        
        # 如果有上傳檔案，將檔案內容加入 Prompt
        if "file_content" in st.session_state and st.session_state["file_content"]:
            final_prompt = f"【檔案內容】\n{st.session_state['file_content']}\n\n請根據上述內容，以『台灣繁體中文』並使用『台灣在地口吻』回答：{prompt}"
            # 清除暫存內容，避免下次對話重複發送
            del st.session_state["file_content"]
            del st.session_state["last_uploaded_file"]
        
        # 先保存基本訊息到 UI
        st.session_state.messages.append({"role": "user", "content": prompt})
        # 保存實際發送給 AI 的完整內容到 pending 狀態
        st.session_state.pending_final_prompt = final_prompt
        st.rerun()

# 加一個腳本底部的強制狀態恢復，防止意外卡死
if st.session_state.is_generating and st.session_state.get("stop_gen", False):
    st.session_state.is_generating = False
    st.session_state.stop_gen = False
    st.rerun()
