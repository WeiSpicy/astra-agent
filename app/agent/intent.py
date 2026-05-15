def detect_intent(user_input: str) -> str:
    if "查" in user_input or "介绍" in user_input:
        return "rag"
    if "计算" in user_input:
        return "tool"
    return "chat"
