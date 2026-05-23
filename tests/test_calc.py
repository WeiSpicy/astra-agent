from app.agent.tools.builtin.calc import calc


class TestCalc:
    def test_basic_addition(self):
        result = calc("1 + 2")
        assert result == "3"

    def test_multiplication(self):
        assert calc("7 * 8") == "56"

    def test_division(self):
        assert calc("10 / 4") == "2.5"

    def test_floor_division(self):
        assert calc("10 // 4") == "2"

    def test_modulo(self):
        assert calc("10 % 3") == "1"

    def test_power(self):
        assert calc("2 ** 10") == "1024"

    def test_negative_number(self):
        assert calc("-5 + 3") == "-2"

    def test_decimal(self):
        assert calc("3.14 * 2") == "6.28"

    def test_parentheses(self):
        assert calc("(1 + 2) * 3") == "9"

    def test_nested_parentheses(self):
        assert calc("((2 + 3) * 4) / 2") == "10.0"

    def test_sqrt(self):
        assert calc("sqrt(16)") == "4.0"

    def test_sin_zero(self):
        assert calc("sin(0)") == "0.0"

    def test_constant_pi(self):
        result = float(calc("pi"))
        assert abs(result - 3.141592653589793) < 1e-10

    def test_constant_e(self):
        result = float(calc("e"))
        assert abs(result - 2.718281828459045) < 1e-10

    def test_division_by_zero(self):
        result = calc("1 / 0")
        assert "除以零" in result

    def test_unary_plus_rejected(self):
        assert "不支持" in calc("+5")

    def test_unsafe_function(self):
        result = calc("__import__('os')")
        assert "不支持" in result

    def test_empty_expression(self):
        result = calc("")
        assert "语法错误" in result or "失败" in result

    def test_whitespace_only(self):
        result = calc("   ")
        assert "语法错误" in result or "失败" in result
