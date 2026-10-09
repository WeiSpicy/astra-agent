import streamlit as st
import requests
import json
import os
import uuid

# =========================
# 页面配置
# =========================
st.set_page_config(page_title="Astra Agent", page_icon="🤖")

st.title("Astra Agent Demo")
st.caption("一个支持 Tool Calling · RAG · Streaming 的 AI Agent Demo")

# =========================
# Dark / Light 主题样式切换
# =========================
current_theme = getattr(st.context.theme, "type", "light")

if current_theme == "dark":
    theme_colors = {
        "user_bg": "rgba(255, 255, 255, 0.1)",
        "user_border": "rgba(255, 255, 255, 0.2)",
        "assistant_bg": "rgba(255, 255, 255, 0.05)",
        "assistant_border": "rgba(255, 255, 255, 0.15)",
        "tool_bg": "rgba(255, 255, 255, 0.05)",
        "tool_border": "rgba(255, 255, 255, 0.15)",
    }
else:
    theme_colors = {
        "user_bg": "rgba(0, 120, 212, 0.15)",
        "user_border": "rgba(0, 120, 212, 0.35)",
        "assistant_bg": "rgba(0, 0, 0, 0.05)",
        "assistant_border": "rgba(0, 0, 0, 0.1)",
        "tool_bg": "rgba(0, 0, 0, 0.05)",
        "tool_border": "rgba(0, 0, 0, 0.1)",
    }

unified_css = f"""
<style>
/* 1. 基础布局骨架 */
.chat-row {{
    display: flex;
    align-items: flex-start;
    margin-bottom: 12px;
}}

.chat-bubble {{
    padding: 10px 14px;
    border-radius: 12px;
    max-width: 80%;
    line-height: 1.5;
    font-size: 15px;
    color: var(--text-color);
}}

.user-bubble {{
    background-color: {theme_colors['user_bg']};
    border: 1px solid {theme_colors['user_border']};
    margin-left: auto;
    margin-right: 0;
}}

.assistant-bubble {{
    background-color: {theme_colors['assistant_bg']};
    border: 1px solid {theme_colors['assistant_border']};
    margin-right: auto;
}}

.tool-box {{
    background-color: {theme_colors['tool_bg']};
    border: 1px solid {theme_colors['tool_border']};
    padding: 8px 12px;
    border-radius: 8px;
    margin-top: 6px;
    font-size: 13px;
    color: var(--text-color);
}}

.loading-dots {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 20px;
    margin-right: 10px;
}}

.loading-dots span {{
    width: 6px;
    height: 6px;
    margin: 0 2px;
    background-color: #2b8cff;
    border-radius: 50%;
    display: inline-block;
    animation: loading-dots 1.4s infinite ease-in-out both;
}}

.loading-dots span:nth-child(1) {{ animation-delay: -0.32s; }}
.loading-dots span:nth-child(2) {{ animation-delay: -0.16s; }}

@keyframes loading-dots {{
    0%, 80%, 100% {{ transform: scale(0); }}
    40% {{ transform: scale(1); }}
}}

.cursor {{
    animation: blink 1s infinite;
}}

@keyframes blink {{
    0% {{ opacity: 1; }}
    50% {{ opacity: 0; }}
    100% {{ opacity: 1; }}
}}
</style>
"""

st.markdown(unified_css, unsafe_allow_html=True)

# =========================
# 后端请求地址
# =========================
BACKEND_URL = "http://127.0.0.1:8000"

# 与后端共享的令牌；非空时请求带上 Authorization 头，为空则不带（本地开发）
ASTRA_API_TOKEN = os.getenv("ASTRA_API_TOKEN", "")
AUTH_HEADERS = (
    {"Authorization": f"Bearer {ASTRA_API_TOKEN}"} if ASTRA_API_TOKEN else {}
)

# =========================
# 设置对话session id
# =========================
if "session_id" not in st.session_state:
    saved_id = st.context.cookies.get("astra_session_id")

    if saved_id:
        st.session_state.session_id = saved_id
    else:
        new_id = str(uuid.uuid4())
        st.session_state.session_id = new_id

        st.components.v1.html(
            f"""
            <script>
                const date = new Date();
                date.setTime(date.getTime() + (7 * 24 * 60 * 60 * 1000));
                document.cookie = "astra_session_id={new_id}; expires=" + date.toUTCString() + "; path=/";
            </script>
            """,
            height=0,
        )

# 输入框状态控制
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False


# =========================
# 初始化聊天历史
# =========================
def fetch_history():
    try:
        res = requests.get(
            f"{BACKEND_URL}/api/v1/memory/history?session_id={st.session_state.session_id}&limit=10"
        )
        return res.json().get("data", [])
    except:
        return []


if "messages" not in st.session_state:
    backend_history = fetch_history()

    if backend_history:
        st.session_state.messages = backend_history
    else:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": """嗨！我是 AstraAgent 👋
一个具备动态工作流与并发调度能力的 AI 助手。你可以这样考考我：\n
🌤️ 查工具：“今天厦门和杭州天气怎么样？ 今天几号或者一些简单的数学运算。”\n
📚 查知识：本地 RAG 管道已跑通！现阶段可以问我 FastAPI、Python 异步编程等技术概念。\n
我的知识库正在疯狂扩容中，现在想对我说点什么呢？""",
                "tools": None,
            }
        ]


# =========================
# 流式 SSE 处理函数
# =========================
def stream_response(question: str):
    """通过 SSE 获取流式结果"""

    url = f"{BACKEND_URL}/api/v1/chat/stream"

    try:
        response = requests.post(
            url,
            json={"question": question, "session_id": st.session_state.session_id},
            headers=AUTH_HEADERS,
            stream=True,
            timeout=120,
        )

        for line in response.iter_lines():

            if not line:
                continue

            line = line.decode("utf-8")

            if line.startswith("data: "):

                data_str = line[6:]

                try:
                    data = json.loads(data_str)
                    yield data

                except Exception as e:
                    yield {"type": "error", "content": f"SSE JSON 解析失败: {e}"}

    except Exception as e:
        yield {"type": "error", "content": f"连接后端失败: {e}"}


# =========================
# 消息渲染
# =========================
def render_message(msg):
    bubble_class = "assistant-bubble" if msg["role"] == "assistant" else "user-bubble"

    st.markdown(
        f"""
        <div class="chat-row">
            <div class="chat-bubble {bubble_class}">
                {msg["content"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# 渲染历史
for msg in st.session_state.messages:
    render_message(msg)


# =========================
# 状态展示
# =========================
def render_status(placeholder, content: str, is_loading: bool = True):
    """显示执行状态 + loading 动画"""
    if is_loading:
        loading_html = """
        <div style="display: flex; align-items: center; gap: 12px;">
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <span>{content}</span>
        </div>
        """.format(content=content)
    else:
        loading_html = f"<span>{content}</span>"

    placeholder.markdown(
        f"""
        <div style="padding: 12px 16px; 
                    background: rgba(255,255,255,0.06); 
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 12px; 
                    margin: 8px 0;">
            {loading_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# 输入框
# =========================
prompt = st.chat_input(
    "请输入你的问题…", disabled=st.session_state.get("is_processing", False)
)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    st.session_state.is_processing = True
    st.rerun()

if st.session_state.get("is_processing", False):
    status_placeholder = st.empty()
    answer_placeholder = st.empty()
    full_answer = ""

    render_status(status_placeholder, "等待 AI 思考中...", is_loading=True)

    current_prompt = st.session_state.messages[-1]["content"]

    for event in stream_response(current_prompt):
        event_type = event.get("event")
        content = event.get("content") or event.get("message", "")

        if event_type in ["status", "llm_start"]:
            render_status(status_placeholder, content, is_loading=True)

        elif event_type == "steps":
            render_status(status_placeholder, content, is_loading=False)
        elif event_type == "token":
            full_answer += content

            answer_placeholder.markdown(
                f"""
                <div class="chat-row">
                    <div class="chat-bubble assistant-bubble">
                        {full_answer}<span class="cursor">|</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        elif event_type == "final":
            full_answer = content
            answer_placeholder.markdown(
                f"""
                <div class="chat-row">
                    <div class="chat-bubble assistant-bubble">
                        {full_answer}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            status_placeholder.empty()

        elif event_type == "error":
            # 错误消息入历史再 rerun, 否则重绘后提示丢失
            st.session_state.messages.append(
                {"role": "assistant", "content": f"⚠️ {content or '发生错误'}"}
            )
            st.session_state.is_processing = False
            st.rerun()

    # 保存到历史记录
    if full_answer:        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": full_answer,
            }
        )

    st.session_state.is_processing = False
    st.rerun()
