import streamlit as st
import requests
import json
import uuid

# =========================
# 页面配置
# =========================
st.set_page_config(page_title="Astra Agent", page_icon="🤖")

st.title("Astra Agent Demo")
st.caption("一个支持 Tool Calling · RAG · Streaming 的 AI Agent Demo")

# =========================
# 主题检测与差异化颜色 Token
# =========================
current_theme = getattr(st.context.theme, "type", "light")

# 提取纯颜色样式差异，做成配置字典
if current_theme == "dark":
    theme_colors = {
        "user_bg": "rgba(255, 255, 255, 0.1)",
        "user_border": "rgba(255, 255, 255, 0.2)",
        "assistant_bg": "rgba(255, 255, 255, 0.05)",
        "assistant_border": "rgba(255, 255, 255, 0.15)",
        "tool_bg": "rgba(255, 255, 255, 0.05)",
        "tool_border": "rgba(255, 255, 255, 0.15)"
    }
else:
    theme_colors = {
        "user_bg": "rgba(0, 120, 212, 0.15)",
        "user_border": "rgba(0, 120, 212, 0.35)",
        "assistant_bg": "rgba(0, 0, 0, 0.05)",
        "assistant_border": "rgba(0, 0, 0, 0.1)",
        "tool_bg": "rgba(0, 0, 0, 0.05)",
        "tool_border": "rgba(0, 0, 0, 0.1)"
    }

# =========================
# 统一的 CSS 架构模板（利用 f-string 动态注入颜色）
# =========================
# 注意：CSS 原生的大括号 {} 在 f-string 中需要写成双大括号 {{}} 规避转义
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

/* 2. 差异化皮肤注入 */
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

/* 3. Loading 动画组件（统一管理，绝不复制第二遍） */
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

<style>
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

# 一行代码注入干净的样式
st.markdown(unified_css, unsafe_allow_html=True)

# =========================
# 后端请求地址
# =========================
BACKEND_URL = "http://127.0.0.1:8000"

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
        
        # 利用 JS 写入Cookie并设置七天有效期
        st.components.v1.html(
            f"""
            <script>
                const date = new Date();
                date.setTime(date.getTime() + (7 * 24 * 60 * 60 * 1000));
                document.cookie = "astra_session_id={new_id}; expires=" + date.toUTCString() + "; path=/";
            </script>
            """,
            height=0, # 隐藏组件，不占用任何页面视觉空间
        )

# =========================
# 工具链展示
# =========================
def render_tool_chain(tools):
    if not tools:
        return
    st.markdown("**🛠 工具调用链**")
    st.code(json.dumps(tools, ensure_ascii=False, indent=2), language="json")

# =========================
# 初始化聊天历史
# =========================
def fetch_history():
    try:
        res = requests.get(f"{BACKEND_URL}/api/v1/memory/history?session_id={st.session_state.session_id}&limit=10")
        return res.json().get("data", [])
    except:
        return []

if "messages" not in st.session_state:
    # 💡 核心改动：优先去拿后端的历史
    backend_history = fetch_history()
    
    if backend_history:
        # 如果后端有历史，直接接过来
        st.session_state.messages = backend_history
    else:
        # 如果后端是空的（比如刚开机），才用默认欢迎语
        st.session_state.messages = [
            {"role": "assistant", "content": "你好，我是 AstraAgent！有什么可以帮你的吗？", "tools": None}
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
            json={
                "question": question,
                "session_id": st.session_state.session_id
            },
            stream=True,
            timeout=120,
        )

        for line in response.iter_lines():

            if not line:
                continue

            line = line.decode("utf-8")

            # SSE 格式: data: {...}
            if line.startswith("data: "):

                data_str = line[6:]

                try:
                    data = json.loads(data_str)
                    yield data

                except Exception as e:
                    yield {
                        "type": "error",
                        "content": f"SSE JSON 解析失败: {e}"
                    }

    except Exception as e:
        yield {
            "type": "error",
            "content": f"连接后端失败: {e}"
        }
            
# =========================
# 渲染消息
# =========================
def render_message(msg):
    role = msg["role"]
    bubble_class = "assistant-bubble" if role == "assistant" else "user-bubble"

    # 助手：左侧
    if role == "assistant":
        st.markdown(
            f"""
            <div class="chat-row">
                <div class="chat-bubble {bubble_class}">
                    {msg["content"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    # 用户：右侧
    else:
        st.markdown(
            f"""
            <div class="chat-row" style="justify-content: flex-end;">
                <div class="chat-bubble {bubble_class}">
                    {msg["content"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    render_tool_chain(msg.get("tools"))

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
        unsafe_allow_html=True
    )
# =========================
# 输入框
# =========================
prompt = st.chat_input("请输入你的问题…")

if prompt:

    # -------------------------
    # 显示用户消息
    # -------------------------
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    render_message(st.session_state.messages[-1])

    # -------------------------
    # 动态区域
    # -------------------------
    status_placeholder = st.empty()
    answer_placeholder = st.empty()
    full_answer = ""

    # 请求前显示“等待 AI 思考中”
    render_status(status_placeholder, "等待 AI 思考中...", is_loading=True)
    
    # -------------------------
    # SSE 流式接收
    # -------------------------
    for event in stream_response(prompt):
        event_type = event.get("event")
        content = event.get("content") or event.get("message", "")

        if event_type in ["status", "step_start", "tool_start", "rag_start", "llm_start"]:
            render_status(status_placeholder, content, is_loading=True)

        elif event_type in ["tool_result", "rag_result", "steps"]:
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
                unsafe_allow_html=True
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
                unsafe_allow_html=True
            )
            status_placeholder.empty()        # 最终答案出来后清除状态栏

        elif event_type == "error":
            render_status(status_placeholder, content or "发生错误", is_loading=False)

    # -------------------------
    # 保存到历史记录
    # -------------------------

    if full_answer:

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_answer,
        })