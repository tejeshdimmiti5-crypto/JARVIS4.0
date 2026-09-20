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


def test_progress_summary_tool():
    result = run_tool("progress_summary", {"tasks": [{"completed": 1}, {"completed": 0}]})
    assert result["total_tasks"] == 2
    assert result["completed_tasks"] == 1
    assert result["completion_percent"] == 50.0


def test_planner_summary_tool():
    result = run_tool("planner_summary", {"tasks": [{"title": "DSA", "completed": 0}, {"title": "ML", "completed": 1}]})
    assert result["pending_tasks"] == 1
    assert result["tasks"] == ["DSA"]


def test_study_command_parser():
    from app.tools import tool_for_text
    assert tool_for_text("show my planner") == ("planner_summary", {"tasks": []})
    assert tool_for_text("show my progress") == ("progress_summary", {"tasks": []})


def test_study_dashboard_tool():
    result = run_tool("study_dashboard", {"subjects": ["ML"], "notes": ["Unit 1"], "tasks": [{"title": "DSA", "completed": 0}, {"title": "Python", "completed": 1}]})
    assert result["task_count"] == 2
    assert result["completed_tasks"] == 1
    assert result["completion_percent"] == 50.0
    assert result["pending_tasks"] == ["DSA"]


def test_daily_briefing_tool():
    result = run_tool("daily_briefing", {"subjects": ["ML", "DSA"], "notes": ["Unit 1"], "tasks": [{"title": "Revise ML", "completed": 0, "minutes": 45}, {"title": "DSA", "completed": 1, "minutes": 30}]})
    assert result["subject_count"] == 2
    assert result["pending_task_count"] == 1
    assert result["planned_minutes"] == 45


def test_focus_recommendation_tool():
    result = run_tool("focus_recommendation", {"subjects": ["ML"], "tasks": [{"title": "Revise Unit 1", "completed": 0, "minutes": 45, "task_date": "2026-09-20"}, {"title": "Done", "completed": 1, "minutes": 30, "task_date": "2026-09-20"}]})
    assert result["focus"] == "Revise Unit 1"
    assert result["pending_tasks"] == 1
