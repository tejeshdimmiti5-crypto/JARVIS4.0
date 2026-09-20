from __future__ import annotations

import ast
import math
import operator
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: Callable[[dict[str, Any]], Any]


def _calculate_expression(expression: str) -> float | int:
    expression = expression.strip()
    if not expression or len(expression) > 500:
        raise ValueError("Expression is empty or too long")
    allowed_binops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
    allowed_unary = {ast.UAdd: operator.pos, ast.USub: operator.neg}
    allowed_names = {"pi": math.pi, "e": math.e}
    def evaluate(node: ast.AST) -> float | int:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.Name) and node.id in allowed_names:
            return allowed_names[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in allowed_binops:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("Exponent is too large")
            return allowed_binops[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed_unary:
            return allowed_unary[type(node.op)](evaluate(node.operand))
        raise ValueError("Only arithmetic expressions are allowed")
    try:
        result = evaluate(ast.parse(expression, mode="eval").body)
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Invalid arithmetic expression") from exc
    if not math.isfinite(float(result)) or abs(float(result)) > 1e100:
        raise ValueError("Result is outside the supported range")
    return result


def time_tool(args: dict[str, Any]) -> dict[str, Any]:
    zone = str(args.get("timezone", "UTC")).strip() or "UTC"
    try:
        tz = ZoneInfo(zone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown timezone") from exc
    now = datetime.now(tz)
    return {"timezone": zone, "date": now.date().isoformat(), "time": now.strftime("%H:%M:%S"), "iso": now.isoformat()}


def calculator_tool(args: dict[str, Any]) -> dict[str, Any]:
    expression = str(args.get("expression", ""))
    return {"expression": expression, "result": _calculate_expression(expression)}


def study_summary_tool(args: dict[str, Any]) -> dict[str, Any]:
    subjects = args.get("subjects", [])
    if not isinstance(subjects, list):
        raise ValueError("subjects must be a list")
    return {"subject_count": len(subjects), "subjects": [str(s)[:100] for s in subjects[:20]]}


def notes_summary_tool(args: dict[str, Any]) -> dict[str, Any]:
    notes = args.get("notes", [])
    if not isinstance(notes, list):
        raise ValueError("notes must be a list")
    return {"note_count": len(notes), "notes": [str(n)[:200] for n in notes[:10]]}


def progress_summary_tool(args: dict[str, Any]) -> dict[str, Any]:
    tasks = args.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    total = len(tasks)
    completed = sum(1 for t in tasks if isinstance(t, dict) and (t.get("completed") in {1, True, "1", "true"} or str(t.get("status", "")).lower() in {"done", "completed"}))
    return {"total_tasks": total, "completed_tasks": completed, "completion_percent": round((completed / total) * 100, 1) if total else 0}


def planner_summary_tool(args: dict[str, Any]) -> dict[str, Any]:
    tasks = args.get("tasks", [])
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    pending = [t for t in tasks if isinstance(t, dict) and not (t.get("completed") in {1, True, "1", "true"} or str(t.get("status", "")).lower() in {"done", "completed"})]
    return {"pending_tasks": len(pending), "tasks": [str(t.get("title", ""))[:120] for t in pending[:10]]}


TOOLS: dict[str, ToolDefinition] = {
    "study_summary": ToolDefinition("study_summary", "Summarize the supplied study subject list.", study_summary_tool),
    "progress_summary": ToolDefinition("progress_summary", "Summarize study task completion progress.", progress_summary_tool),
    "planner_summary": ToolDefinition("planner_summary", "Show pending study tasks for planning.", planner_summary_tool),
    "study_dashboard": ToolDefinition("study_dashboard", "Summarize subjects, notes, and study task progress.", study_dashboard_tool),
    "study_dashboard": ToolDefinition("study_dashboard", "Summarize subjects, notes, and study task progress.", study_dashboard_tool),
    "notes_summary": ToolDefinition("notes_summary", "Summarize a supplied list of saved notes.", notes_summary_tool),
    "time": ToolDefinition("time", "Return the current date and time for a timezone.", time_tool),
    "calculator": ToolDefinition("calculator", "Safely evaluate basic arithmetic expressions.", calculator_tool),
}


def list_tools() -> list[dict[str, str]]:
    return [{"name": tool.name, "description": tool.description} for tool in TOOLS.values()]


def tool_for_text(text: str) -> tuple[str, dict[str, Any]] | None:
    import re
    q = text.strip().lower()
    if q in {"time", "what time is it", "current time", "date today", "what is today"}:
        return "time", {}
    if q in {"show my subjects", "my subjects", "list my subjects"}:
        return "study_summary", {"subjects": []}
    if q in {"show my notes", "my notes", "list my notes"}:
        return "notes_summary", {"notes": []}
    if q in {"show my progress", "my progress", "study progress", "how am i doing"}:
        return "progress_summary", {"tasks": []}
    if q in {"show my planner", "my planner", "study planner", "what should i study"}:
        return "planner_summary", {"tasks": []}
    if q in {"show my dashboard", "my dashboard", "study dashboard", "jarvis dashboard"}:
        return "study_dashboard", {}
    match = re.search(r"(?:calculate|what is)\s+([0-9pi e+\-*/().%]+)$", q)
    if not match:
        return None
    return "calculator", {"expression": match.group(1).replace(" ", "")}


def run_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    tool = TOOLS.get(name)
    if tool is None:
        raise KeyError(f"Unknown tool: {name}")
    return tool.handler(args)

def study_dashboard_tool(args: dict[str, Any]) -> dict[str, Any]:
    subjects = args.get("subjects", [])
    notes = args.get("notes", [])
    tasks = args.get("tasks", [])
    if not all(isinstance(v, list) for v in (subjects, notes, tasks)):
        raise ValueError("dashboard data must be lists")
    completed = sum(1 for t in tasks if isinstance(t, dict) and (t.get("completed") in {1, True, "1", "true"} or str(t.get("status", "")).lower() in {"done", "completed"}))
    pending = [t for t in tasks if isinstance(t, dict) and not (t.get("completed") in {1, True, "1", "true"} or str(t.get("status", "")).lower() in {"done", "completed"})]
    return {
        "subjects": [str(s)[:100] for s in subjects[:20]],
        "note_count": len(notes),
        "task_count": len(tasks),
        "completed_tasks": completed,
        "completion_percent": round((completed / len(tasks)) * 100, 1) if tasks else 0,
        "pending_tasks": [str(t.get("title", ""))[:120] for t in pending[:10]],
    }
def study_dashboard_tool(args: dict[str, Any]) -> dict[str, Any]:
    subjects = args.get("subjects", [])
    notes = args.get("notes", [])
    tasks = args.get("tasks", [])
    if not all(isinstance(v, list) for v in (subjects, notes, tasks)):
        raise ValueError("dashboard data must be lists")
    completed = sum(1 for t in tasks if isinstance(t, dict) and (t.get("completed") in {1, True, "1", "true"} or str(t.get("status", "")).lower() in {"done", "completed"}))
    pending = [t for t in tasks if isinstance(t, dict) and not (t.get("completed") in {1, True, "1", "true"} or str(t.get("status", "")).lower() in {"done", "completed"})]
    return {"subjects": [str(s)[:100] for s in subjects[:20]], "note_count": len(notes), "task_count": len(tasks), "completed_tasks": completed, "completion_percent": round((completed / len(tasks)) * 100, 1) if tasks else 0, "pending_tasks": [str(t.get("title", ""))[:120] for t in pending[:10]]}



