from app.tools import list_tools, run_tool


def test_calculator_tool():
    assert run_tool("calculator", {"expression": "2 + 3 * 4"})["result"] == 14


def test_calculator_supports_constants():
    result = run_tool("calculator", {"expression": "pi * 2"})["result"]
    assert round(result, 6) == 6.283185


def test_calculator_rejects_code():
    try:
        run_tool("calculator", {"expression": "__import__('os').getcwd()"})
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe expression was accepted")


def test_tool_registry():
    names = {item["name"] for item in list_tools()}
    assert "calculator" in names


def test_natural_language_calculation_parser():
    from app.tools import tool_for_text
    assert tool_for_text("calculate 25 * 4") == ("calculator", {"expression": "25*4"})
