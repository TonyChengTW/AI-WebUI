import os
import time
import datetime
import extra_streamlit_components as stx
import streamlit as st
import requests
import json
import uuid
import re
import matplotlib
import matplotlib.pyplot as plt
import io
import hashlib
import textwrap
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document

# Force non-interactive backend for server stability
matplotlib.use('Agg')

# --- Header & Initialization ---
st.set_page_config(page_title="AI 小幫手", page_icon="🤖", layout="wide")

TITLE_HTML = """
<div id="main-header" style="padding: 10px 0px; margin-bottom: 20px; border-bottom: 1px solid #444;">
    <h1 style="margin: 0; font-size: 2.5rem;">💬 AI小幫手</h1>
</div>
"""

# Default Technical Prompt
DEFAULT_TECH = """你是一個技術專家。請遵守以下原則：
1. **按需生成**：只有在使用者要求繪圖或寫程式時才產生代碼，平時請以聊天為主。
2. **變數名稱禁中化**：程式碼中的變數名與函數名必須使用英文。
3. **中文僅限標籤**：只有圖表的 title, xlabel, ylabel 可使用繁體中文。
4. **區塊一體化**：所有繪圖代碼必須寫在同一個代碼區塊內。"""

# Default Persona Prompt
DEFAULT_PERSONA = "使用台灣繁體中文回覆，語調像一個熱心且專業的小幫手。"

# Initialize Cookie Manager
cookie_manager = stx.CookieManager()

# --- Helper for Rendering Content ---
def render_content(content, block_id=""):
    if not content or content.strip() == "": return
    pattern = r"(?:```(mermaid|dot|graphviz|python|py|python3|)\b(.*?)\n?```|<(mermaid|dot|graphviz|python|py|python3)>(.*?)</\3>)"
    last_idx = 0
    matches = list(re.finditer(pattern, content, flags=re.DOTALL | re.IGNORECASE))
    if not matches:
        st.markdown(content); return
    for match in matches:
        start, end = match.span()
        if pre := content[last_idx:start].strip(): st.markdown(pre)
        lang = (match.group(1) or match.group(3) or "").lower().strip()
        code = (match.group(2) or match.group(4) or "").strip()
        if lang in ["py", "python3"]: lang = "python"
        if lang == "" and any(ind in code.lower() for ind in ["plt.", "matplotlib", "sns."]): lang = "python"
        
        if lang == "mermaid":
            st.components.v1.html(
                f'<div class="mermaid" style="display:flex;justify-content:center;background:white;padding:10px;border-radius:8px;">{code}</div>'
                f'<script type="module">import m from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";m.initialize({{startOnLoad:true}});</script>',
                height=400, scrolling=True
            )
        elif lang in ["dot", "graphviz"]:
            st.graphviz_chart(code, use_container_width=True)
        elif lang == "python":
            st.code(code, language="python")
            if any(ind in code.lower() for ind in ["plt.", "matplotlib", "fig", "dot.", "graphviz", "digraph", "sns."]):
                btn_key = f"plot_btn_{hashlib.md5((code + block_id).encode()).hexdigest()[:8]}"
                if st.button("📈 執行並顯示圖表", key=btn_key):
                    try:
                        import numpy as np, pandas as pd, graphviz
                        from datetime import datetime, timedelta
                        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Arial Unicode MS', 'sans-serif']
                        plt.rcParams['axes.unicode_minus'] = False
                        exec_code = textwrap.dedent(code)
                        exec_code = re.sub(r"plt\.show\(.*\)", "", exec_code)
                        exec_code = re.sub(r"\.render\(.*\)", "", exec_code)
                        alias_prefix = """
import graphviz, matplotlib.pyplot as plt, numpy as np, pandas as pd
from datetime import datetime, timedelta
_v = locals().copy()
if '月份' in _v: months = month = x = _v['月份']
if '氣溫' in _v: temperatures = temperature = temp = y = _v['氣溫']
_p = graphviz.Digraph(); _o = _p.attr
def _fa(*a, **k):
    if len(a)==2 and a[0]=='label' and 'graph' not in k: return _o('graph', label=a[1])
    return _o(*a, **k)
_p.attr = _fa
class _DF: def __new__(cls, *args, **kw): return _p
graphviz.Digraph = _DF; dot = digraph = _p
"""
                        plt.close('all'); plt.clf()
                        ls = {"plt": plt, "np": np, "pd": pd, "datetime": datetime, "timedelta": timedelta, "graphviz": graphviz, "st": st}
                        exec(alias_prefix + "\n" + exec_code, {}, ls)
                        if 'dot' in ls or 'digraph' in ls: st.graphviz_chart(ls.get('dot') or ls.get('digraph'))
                        else: st.pyplot(plt.gcf())
                    except Exception as e: st.error(f"❌ 執行錯誤: {e}")
                    finally: plt.close('all')
        else: st.code(code, language=lang or "text")
        last_idx = end
    if post := content[last_idx:].strip(): st.markdown(post)

# --- State ---
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if "messages" not in st.session_state: st.session_state.messages = []
if "is_generating" not in st.session_state: st.session_state.is_generating = False
if "tech_prompt" not in st.session_state: st.session_state.tech_prompt = DEFAULT_TECH
if "user_prompt" not in st.session_state: st.session_state.user_prompt = DEFAULT_PERSONA
if "models_hiding" not in st.session_state: st.session_state.models_hiding = []
if "sync_count" not in st.session_state: st.session_state.sync_count = 0
if "file_content" not in st.session_state: st.session_state.file_content = ""

def get_history_path():
    u = st.session_state.get('current_user')
    return f"history_{u}.json" if u else None

def save_history():
    path = get_history_path()
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)

# --- Auth Persistence ---
if not st.session_state.password_correct:
    all_c = cookie_manager.get_all()
    if all_c and "current_user" in all_c:
        u = all_c["current_user"]
        st.session_state.password_correct, st.session_state.current_user = True, u
        st.session_state.sync_count = 0
        if os.path.exists(f"history_{u}.json"):
            with open(f"history_{u}.json", "r") as f: st.session_state.messages = json.load(f)
        for k in ["tech_prompt", "user_prompt", "models_hiding"]:
            v = all_c.get(k)
            if v:
                if k == "models_hiding": st.session_state[k] = json.loads(v)
                else: st.session_state[k] = v
    else:
        if st.session_state.sync_count < 2:
            st.session_state.sync_count += 1
            with st.spinner("🔄 同步狀態中..."): time.sleep(0.8); st.rerun()

if not st.session_state.get("password_correct"):
    st.markdown("<h1>🔐 AI 系統登入</h1>", unsafe_allow_html=True)
    u_in, p_in = st.text_input("帳號"), st.text_input("密碼", type="password")
    if st.button("進入系統"):
        if u_in in st.secrets["passwords"] and p_in == st.secrets["passwords"][u_in]:
            st.session_state.password_correct, st.session_state.current_user = True, u_in
            cookie_manager.set("current_user", u_in, expires_at=datetime.datetime.now() + datetime.timedelta(days=7))
            st.rerun()
    st.stop()

# --- Sidebar ---
with st.sidebar:
    if st.session_state.is_generating:
        if st.button("🛑 停止生成 (Stop Running)", type="primary", use_container_width=True):
            st.session_state.is_generating = False
            st.rerun()
        st.divider()

    col1, col2 = st.columns([2, 1])
    with col1: st.write(f"👤 **{st.session_state.current_user}**")
    with col2:
        if st.button("🚪 登出"):
            cookie_manager.delete("current_user")
            st.session_state.password_correct = False
            st.session_state.sync_count = 5
            st.rerun()
            
    url = st.text_input("Ollama Host", os.getenv("OLLAMA_HOST", "http://localhost:11434")).strip().rstrip("/")
    try: all_models = [m['name'] for m in requests.get(f"{url}/api/tags").json().get('models', [])]
    except: all_models = []
    
    st.subheader("� 檔案上傳 (Knowledge)")
    uploaded_file = st.file_uploader("上傳 PDF, Word, CSV 或純文字檔", type=["pdf", "docx", "txt", "csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".pdf"):
                reader = PdfReader(uploaded_file)
                st.session_state.file_content = "\n".join([page.extract_text() for page in reader.pages])
            elif uploaded_file.name.endswith(".docx"):
                doc = Document(uploaded_file)
                st.session_state.file_content = "\n".join([para.text for para in doc.paragraphs])
            elif uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
                st.session_state.file_content = df.to_string()
            elif uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file)
                st.session_state.file_content = df.to_string()
            else:
                st.session_state.file_content = uploaded_file.read().decode("utf-8")
            st.success(f"已讀取檔案: {uploaded_file.name}")
        except Exception as e:
            st.error(f"檔案讀取失敗: {e}")
    else:
        st.session_state.file_content = ""

    st.subheader("�🛠️ 管理")
    sel_h = st.multiselect("隱藏模型清單", sorted(all_models), default=st.session_state.models_hiding)
    if st.button("更新設定"):
        st.session_state.models_hiding = sel_h
        cookie_manager.set("models_hiding", json.dumps(sel_h), expires_at=datetime.datetime.now() + datetime.timedelta(days=7))
        st.rerun()

    visible = [m for m in all_models if m not in st.session_state.models_hiding]
    sel_model = st.selectbox("選模型", sorted(visible or all_models))
    st.divider()
    with st.expander("⚙️ 技術架構規範 (Technical)", expanded=False):
        tp = st.text_area("設定技術準則", st.session_state.tech_prompt, height=220, label_visibility="collapsed")
        if tp != st.session_state.tech_prompt:
            st.session_state.tech_prompt = tp
            cookie_manager.set("tech_prompt", tp, expires_at=datetime.datetime.now() + datetime.timedelta(days=7))
    with st.expander("🎭 說話風格人格 (Persona)", expanded=False):
        up = st.text_area("設定風格人格", st.session_state.user_prompt, height=180, label_visibility="collapsed")
        if up != st.session_state.user_prompt:
            st.session_state.user_prompt = up
            cookie_manager.set("user_prompt", up, expires_at=datetime.datetime.now() + datetime.timedelta(days=7))
    if st.button("🗑️ 清空紀錄"): 
        st.session_state.messages = []; save_history(); st.rerun()

# --- Main Layout ---
st.markdown(TITLE_HTML, unsafe_allow_html=True)
for idx, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]): render_content(m["content"], f"m_{idx}")

# --- Generation Logic ---
if st.session_state.is_generating:
    with st.chat_message("assistant"):
        ai_msg_placeholder = st.empty()
        if st.button("🛑 停止生成 (Stop Running)", type="primary", use_container_width=True):
            st.session_state.is_generating = False
            st.rerun()
            
        with st.status("AI 運算中...", expanded=True) as status:
            f_actual = ""
            # Inject File Content if exists
            context_prefix = ""
            if st.session_state.file_content:
                context_prefix = f"[附帶檔案內容作為參考]:\n{st.session_state.file_content}\n\n"
            
            comb = f"{st.session_state.tech_prompt}\n\n{st.session_state.user_prompt}"
            msgs = [{"role": "system", "content": comb}]
            for m in st.session_state.messages[:-1]: msgs.append({"role": m["role"], "content": m["content"]})
            
            # Use current prompt with context
            last_user_msg = st.session_state.pending_prompt
            if context_prefix:
                last_user_msg = context_prefix + last_user_msg
            
            msgs.append({"role": "user", "content": last_user_msg})
            
            try:
                with requests.post(f"{url}/api/chat", json={"model": sel_model, "messages": msgs, "stream": True}, stream=True) as r:
                    for line in r.iter_lines():
                        if not st.session_state.is_generating: break
                        if line:
                            resp = json.loads(line).get("message", {})
                            ct = resp.get("content", "")
                            if ct:
                                f_actual += ct
                                ai_msg_placeholder.markdown(f_actual + "▌")
                status.update(label="完成", state="complete", expanded=False)
            except Exception as e: st.error(f"Error: {e}"); status.update(label="失敗", state="error")
            
            if st.session_state.is_generating:
                st.session_state.messages.append({"role": "assistant", "content": f_actual})
                save_history()
            st.session_state.is_generating = False
            st.rerun()
else:
    if p := st.chat_input("發送訊息..."):
        st.session_state.is_generating, st.session_state.pending_prompt = True, p
        st.session_state.messages.append({"role": "user", "content": p})
        st.rerun()
