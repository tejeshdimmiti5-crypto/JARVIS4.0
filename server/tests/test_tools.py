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


def test_time_tool():
    result = run_tool("time", {})
    assert result["date"]
    assert result["time"]

def test_natural_language_time_tool():
    from app.tools import tool_for_text
    assert tool_for_text("what time is it") == ("time", {})

def test_time_tool_timezone():
    result = run_tool("time", {"timezone": "Asia/Kolkata"})
    assert result["timezone"] == "Asia/Kolkata"
    assert len(result["time"]) == 8

def test_study_summary_tool():
    result = run_tool("study_summary", {"subjects": ["AI", "DSA"]})
    assert result["subject_count"] == 2
