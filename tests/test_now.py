from app.agent.tools.builtin.now import now


class TestNow:
    def test_returns_dict_with_expected_keys(self):
        result = now()
        assert isinstance(result, dict)
        assert "date" in result
        assert "weekday" in result
        assert "time" in result

    def test_date_format(self):
        result = now()
        parts = result["date"].split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # year
        assert 1 <= int(parts[1]) <= 12  # month
        assert 1 <= int(parts[2]) <= 31  # day

    def test_time_format(self):
        result = now()
        parts = result["time"].split(":")
        assert len(parts) == 3
        assert 0 <= int(parts[0]) <= 23  # hour
        assert 0 <= int(parts[1]) <= 59  # minute
        assert 0 <= int(parts[2]) <= 59  # second
