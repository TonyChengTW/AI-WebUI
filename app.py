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
import gc
import sys
import traceback
from PyPDF2 import PdfReader
from docx import Document

# v1.4.9: History Migration Fix & Stability
matplotlib.use('Agg')

# --- Header & Initialization ---
st.set_page_config(page_title="AI 小幫手", page_icon="🤖", layout="wide")

TITLE_HTML = """
<style>
    .stCodeBlock code { font-family: 'Fira Code', 'Monaco', monospace !important; font-size: 0.9rem !important; }
    .stCodeBlock div[data-testid="stCodeBlockLineNumber"] { min-width: 2.5em !important; }
</style>
<div id="main-header" style="padding: 10px 0px; margin-bottom: 20px; border-bottom: 1px solid #444;">
    <h1 style="margin: 0; font-size: 2.5rem;">💬 AI小幫手</h1>
</div>
"""

# Default Prompts
DEFAULT_TECH = """你是一個技術專家。請遵守以下原則：
1. **按需生成**：只有在使用者要求繪圖或寫程式時才產生完整代碼。
2. **預裝環境**：系統已預裝 streamlit, matplotlib, graphviz, networkx, seaborn, scipy, pandas, pillow。
3. **區域化語言** : 台灣繁體中文。
4. **繪圖規範**：變數用英文，標籤可用中文，嚴禁使用 plt.show() 或 dot.render(view=True)。"""
DEFAULT_PERSONA = "語調親切專業，幽默風趣。"

cookie_manager = stx.CookieManager()

def get_history_path():
    u = st.session_state.get('current_user')
    if not u: return None
    os.makedirs("history", exist_ok=True)
    return f"history/history_{u}.json"

def save_history():
    path = get_history_path()
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st.session_state.messages, f, ensure_ascii=False, indent=2)

def render_content(content, block_id="", is_streaming=False):
    if not content or content.strip() == "": return
    clean_content = content.replace("▌", "")
    pattern = r"(?:```(mermaid|dot|graphviz|python|py|python3|)\b(.*?)(?:```|$)|<(mermaid|dot|graphviz|python|py|python3)>(.*?)(?:</\3>|$))"
    last_idx = 0
    for match in re.finditer(pattern, clean_content, flags=re.DOTALL | re.IGNORECASE):
        start, end = match.span()
        if pre := clean_content[last_idx:start].strip(): st.markdown(pre)
        lang = (match.group(1) or match.group(3) or "").lower().strip()
        code = (match.group(2) or match.group(4) or "").strip()
        if lang in ["py", "python3"]: lang = "python"
        if lang == "" and any(ind in code.lower() for ind in ["plt.", "matplotlib", "sns.", "nx.", "networkx"]): lang = "python"
        
        if lang == "mermaid":
            st.components.v1.html(
                f'<div class="mermaid" style="display:flex;justify-content:center;background:white;padding:10px;border-radius:8px;">{code}</div>'
                f'<script type="module">import m from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";m.initialize({{startOnLoad:true}});</script>',
                height=400, scrolling=True
            )
        elif lang in ["dot", "graphviz"]:
            st.graphviz_chart(code, use_container_width=True)
        elif lang == "python":
            st.code(code, language="python", line_numbers=True)
            if not is_streaming and any(ind in code.lower() for ind in ["plt.", "matplotlib", "fig", "dot.", "graphviz", "sns.", "nx.", "networkx"]):
                result_key = hashlib.md5((code + block_id).encode()).hexdigest()[:12]
                if st.button("📈 執行並顯示圖表", key=f"btn_{result_key}"):
                    try:
                        import numpy as np, pandas as pd, graphviz, networkx as nx, seaborn as sns
                        from datetime import datetime, timedelta
                        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Arial Unicode MS', 'sans-serif']
                        plt.rcParams['axes.unicode_minus'] = False
                        fixed_code = code
                        for open_b, close_b in [('[', ']'), ('(', ')'), ('{', '}')]:
                            if fixed_code.count(open_b) > fixed_code.count(close_b): fixed_code += close_b
                        exec_code = textwrap.dedent(fixed_code)
                        exec_code = re.sub(r"plt\.show\(.*\)", "", exec_code)
                        exec_code = re.sub(r"\.render\(.*view\s*=\s*True.*\)", ".render()", exec_code)
                        exec_code = re.sub(r"\.render\(.*\)", "", exec_code)
                        plt.close('all'); plt.clf()
                        namespace = {"plt": plt, "np": np, "pd": pd, "st": st, "nx": nx, "sns": sns, "datetime": datetime, "timedelta": timedelta, "graphviz": graphviz}
                        exec(exec_code, namespace)
                        gv_objs = [v for k, v in namespace.items() if hasattr(v, 'source') and isinstance(v, (graphviz.Digraph, graphviz.Graph))]
                        if gv_objs:
                            img_bytes = gv_objs[-1].pipe(format='png')
                            st.session_state.execution_results[result_key] = {"type": "gv", "data": img_bytes, "obj": gv_objs[-1]}
                        else:
                            buf = io.BytesIO()
                            plt.savefig(buf, format="png", bbox_inches='tight')
                            st.session_state.execution_results[result_key] = {"type": "plt", "data": buf.getvalue()}
                    except Exception as e:
                        print(traceback.format_exc())
                        st.error(f"❌ 執行錯誤: {e}")
                    finally:
                        plt.close('all'); gc.collect()
                if result_key in st.session_state.execution_results:
                    res = st.session_state.execution_results[result_key]
                    st.divider()
                    if res["type"] == "gv": st.graphviz_chart(res["obj"], use_container_width=True)
                    else: st.image(res["data"], use_container_width=True)
                    st.download_button(label="💾 下載圖片 (PNG)", data=res["data"], file_name=f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png", mime="image/png", key=f"dl_{result_key}")
        else: st.code(code, language=lang or "text", line_numbers=True)
        last_idx = end
    if post := clean_content[last_idx:].strip(): st.markdown(post + ("▌" if is_streaming else ""))

# --- State ---
if "password_correct" not in st.session_state: st.session_state.password_correct = False
if "messages" not in st.session_state: st.session_state.messages = []
if "execution_results" not in st.session_state: st.session_state.execution_results = {}
if "is_generating" not in st.session_state: st.session_state.is_generating = False
if "tech_prompt" not in st.session_state: st.session_state.tech_prompt = DEFAULT_TECH
if "user_prompt" not in st.session_state: st.session_state.user_prompt = DEFAULT_PERSONA
if "models_hiding" not in st.session_state: st.session_state.models_hiding = []
if "default_model" not in st.session_state: st.session_state.default_model = None
if "sync_count" not in st.session_state: st.session_state.sync_count = 0
if "file_content" not in st.session_state: st.session_state.file_content = ""

# --- Persistence ---
if not st.session_state.password_correct:
    all_c = cookie_manager.get_all()
    if all_c and "current_user" in all_c:
        u = all_c["current_user"]
        st.session_state.password_correct, st.session_state.current_user = True, u
        # v1.4.9: Recovered Migration Logic
        path = get_history_path()
        if path and os.path.exists(path):
            with open(path, "r") as f: st.session_state.messages = json.load(f)
        elif os.path.exists(f"history_{u}.json"): # Check old root folder
            with open(f"history_{u}.json", "r") as f: 
                st.session_state.messages = json.load(f)
                save_history() # Migrate to history/ folder
        for k in ["tech_prompt", "user_prompt", "models_hiding", "default_model"]:
            v = all_c.get(k)
            if v:
                if k == "models_hiding": st.session_state[k] = json.loads(v)
                else: st.session_state[k] = v
    else:
        if st.session_state.sync_count < 2:
            st.session_state.sync_count += 1
            time.sleep(0.8); st.rerun()

if not st.session_state.get("password_correct"):
    st.markdown("<h1>🔐 AI 系統登入</h1>", unsafe_allow_html=True)
    with st.form("login_form"):
        u_in = st.text_input("帳號", key="login_username")
        p_in = st.text_input("密碼", type="password", key="login_password")
        if st.form_submit_button("進入系統", use_container_width=True):
            if u_in in st.secrets["passwords"] and p_in == st.secrets["passwords"][u_in]:
                st.session_state.password_correct, st.session_state.current_user = True, u_in
                expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=14)
                cookie_manager.set("current_user", u_in, expires_at=expiry)
                st.rerun()
            else: st.error("錯誤")
    st.stop()

# --- Combined UI ---
with st.sidebar:
    col_u, col_l = st.columns([4, 1])
    with col_u: st.write(f"👤 **{st.session_state.current_user}**")
    with col_l:
        if st.button("🚪", help="登出系統"):
            cookie_manager.delete("current_user"); st.session_state.password_correct = False; st.rerun()
    url = st.text_input("Ollama Host", os.getenv("OLLAMA_HOST", "http://localhost:11434")).strip().rstrip("/")
    try:
        resp = requests.get(f"{url}/api/tags", timeout=5)
        all_models = [m['name'] for m in resp.json().get('models', [])]
    except: all_models = []
    st.subheader("📁 檔案上傳")
    uploaded_file = st.file_uploader("文件內容", type=["pdf", "docx", "txt", "csv", "xlsx"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".pdf"):
                st.session_state.file_content = "\n".join([p.extract_text() for p in PdfReader(uploaded_file).pages])
            elif uploaded_file.name.endswith(".docx"):
                st.session_state.file_content = "\n".join([p.text for p in Document(uploaded_file).paragraphs])
            else: st.session_state.file_content = uploaded_file.read().decode("utf-8")
        except: pass
    visible = [m for m in all_models if m not in st.session_state.models_hiding]
    sel_model = st.selectbox("選模型", visible, index=visible.index(st.session_state.default_model) if st.session_state.default_model in visible else 0)
    if st.button("📌 設為預設模型"):
        st.session_state.default_model = sel_model
        cookie_manager.set("default_model", sel_model, expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30))
        st.success(f"已預設: {sel_model}")
    st.divider()
    with st.expander("⚙️ 技術/風格設定"):
        tp = st.text_area("Tech", st.session_state.tech_prompt, height=150)
        up = st.text_area("Persona", st.session_state.user_prompt, height=150)
        if st.button("儲存設定"):
            st.session_state.tech_prompt, st.session_state.user_prompt = tp, up
            cookie_manager.set("tech_prompt", tp, expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=14))
            cookie_manager.set("user_prompt", up, expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=14)); st.success("已儲存")
    if st.button("🗑️ 清空紀錄"): 
        st.session_state.messages = []; st.session_state.execution_results = {}
        save_history(); gc.collect(); st.rerun()

st.markdown(TITLE_HTML, unsafe_allow_html=True)
for idx, m in enumerate(st.session_state.messages):
    with st.chat_message(m["role"]): render_content(m["content"], f"m_{idx}")

if st.session_state.is_generating:
    with st.chat_message("assistant"):
        msg_area = st.empty()
        if st.button("🛑 停止生成", type="secondary"):
            st.session_state.is_generating = False; st.rerun()
        with st.status("AI 運算中...", expanded=True) as status:
            f_actual = ""
            ctx = f"[參考文件]:\n{st.session_state.file_content}\n\n" if st.session_state.file_content else ""
            msgs = [{"role": "system", "content": f"{st.session_state.tech_prompt}\n\n{st.session_state.user_prompt}"}]
            for m in st.session_state.messages[:-1]: msgs.append({"role": m["role"], "content": m["content"]})
            msgs.append({"role": "user", "content": ctx + st.session_state.pending_prompt})
            try:
                with requests.post(f"{url}/api/chat", json={"model": sel_model, "messages": msgs, "stream": True}, stream=True, timeout=60) as r:
                    for line in r.iter_lines():
                        if not st.session_state.is_generating: break
                        if line:
                            resp = json.loads(line).get("message", {})
                            ct = resp.get("content", "")
                            if ct:
                                f_actual += ct
                                with msg_area.container(): render_content(f_actual, is_streaming=True)
                status.update(label="完成", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Error: {e}"); status.update(label="失敗", state="error")
            finally:
                if st.session_state.is_generating:
                    st.session_state.messages.append({"role": "assistant", "content": f_actual}); save_history()
                st.session_state.is_generating = False; gc.collect(); st.rerun()

if not st.session_state.is_generating:
    if p := st.chat_input("發送訊息..."):
        st.session_state.is_generating, st.session_state.pending_prompt = True, p
        st.session_state.messages.append({"role": "user", "content": p}); st.rerun()
