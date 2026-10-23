from app.agent_mode import ALLOWED_AGENT_TOOLS, _context_arguments, fallback_agent_plan, parse_agent_plan


def test_agent_plan_rejects_unregistered_tools_and_caps_steps():
    text = '{"steps":[' + ",".join([
        '{"tool":"daily_briefing","arguments":{},"reason":"brief"}',
        '{"tool":"shell","arguments":{"command":"unsafe"},"reason":"unsafe"}',
        '{"tool":"focus_recommendation","arguments":{},"reason":"focus"}',
        '{"tool":"calculator","arguments":{"expression":"2+2"},"reason":"math"}',
    ]) + ']}'
    plan = parse_agent_plan(text, max_steps=2)
    assert [step["tool"] for step in plan] == ["daily_briefing", "focus_recommendation"]
    assert all(step["tool"] in ALLOWED_AGENT_TOOLS for step in plan)


def test_agent_plan_handles_malformed_json():
    assert parse_agent_plan("not json") == []
    assert parse_agent_plan('{"steps":"not a list"}') == []


def test_fallback_plan_can_chain_read_only_tools():
    plan = fallback_agent_plan("Give me a daily briefing and recommend what I should focus on today")
    assert [step["tool"] for step in plan] == ["daily_briefing", "focus_recommendation"]


def test_fallback_plan_caps_steps():
    plan = fallback_agent_plan("daily briefing focus weekly review dashboard progress", max_steps=2)
    assert len(plan) == 2


def test_user_data_tools_ignore_model_supplied_private_records():
    context = {"subjects": ["Machine Learning"], "notes": ["Revision"], "tasks": [{"title": "Revise Unit 1"}]}
    args = _context_arguments("study_dashboard", context, {
        "subjects": ["someone else's data"], "notes": ["private"], "tasks": [{"title": "injected"}]
    })
    assert args == context


def test_agent_endpoint_requires_authentication():
    from fastapi.testclient import TestClient
    from app.main import app

    response = TestClient(app).post("/api/agent/run", json={"goal": "daily briefing"})
    assert response.status_code in (401, 403)
