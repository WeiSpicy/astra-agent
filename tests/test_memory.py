import pytest
from app.agent.memory import (
    add_message,
    get_history,
    get_recent,
    clear_user_history,
    clear_all_histories,
)
from app.config import MAX_HISTORY


@pytest.fixture(autouse=True)
def clean_memory():
    clear_all_histories()
    yield
    clear_all_histories()


class TestMemory:
    def test_add_and_retrieve(self):
        add_message("user", "你好", "s1")
        add_message("assistant", "你好呀", "s1")

        history = get_history("s1")
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "你好"}
        assert history[1] == {"role": "assistant", "content": "你好呀"}

    def test_default_session(self):
        add_message("user", "hello")
        assert len(get_history()) == 1

    def test_session_isolation(self):
        add_message("user", "A的消息", "s_A")
        add_message("user", "B的消息", "s_B")

        assert len(get_history("s_A")) == 1
        assert len(get_history("s_B")) == 1
        assert get_history("s_A")[0]["content"] == "A的消息"
        assert get_history("s_B")[0]["content"] == "B的消息"

    def test_fifo_overflow(self):
        for i in range(MAX_HISTORY + 5):
            add_message("user", f"msg_{i}", "overflow_test")

        history = get_history("overflow_test")
        assert len(history) == MAX_HISTORY
        assert history[0]["content"] == "msg_5"
        assert history[-1]["content"] == f"msg_{MAX_HISTORY + 4}"

    def test_get_recent(self):
        for i in range(10):
            add_message("user", f"msg_{i}", "recent_test")

        recent = get_recent(limit=3, session_id="recent_test")
        assert len(recent) == 3
        assert recent[0]["content"] == "msg_7"
        assert recent[-1]["content"] == "msg_9"

    def test_clear_single_session(self):
        add_message("user", "要删除的", "to_clear")
        add_message("user", "保留的", "keep")

        clear_user_history("to_clear")

        assert get_history("to_clear") == []
        assert len(get_history("keep")) == 1

    def test_clear_all_sessions(self):
        add_message("user", "s1消息", "s1")
        add_message("user", "s2消息", "s2")

        clear_all_histories()

        assert get_history("s1") == []
        assert get_history("s2") == []

    def test_get_history_on_unknown_session(self):
        assert get_history("never_existed") == []
