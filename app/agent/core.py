from app.agent.intent import detect_intent
from app.agent.rag import rag_query
from app.agent.tools import run_tool
from app.llm.llm_client import chat_with_llm


class AgentCore:
    def __init__(self):
        pass

    def run(self, user_input: str):
        # 1. 意图识别
        intent = detect_intent(user_input)
        
        # 2. RAG（如果意图是查知识）
        docs = []
        if intent == "rag":
            docs = rag_query(user_input)

        # 3. 工具链（如果意图是工具）
        tool_result = None
        if intent == "tool":
            tool_result = run_tool(user_input)

        # 4. 调用 LLM
        answer = chat_with_llm(
            user_input=user_input,
            context_docs=docs,
            tool_result=tool_result
        )

        return {
            "intent": intent,
            "docs": docs,
            "tool_result": tool_result,
            "answer": answer,
        }
