from __future__ import annotations

import ast
import math
import operator
from datetime import datetime, timezone
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

    allowed_binops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
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
    now = datetime.now(timezone.utc)
    return {"utc": now.isoformat(), "date": now.date().isoformat(), "time": now.strftime("%H:%M:%S")}


def calculator_tool(args: dict[str, Any]) -> dict[str, Any]:
    expression = str(args.get("expression", ""))
    return {"expression": expression, "result": _calculate_expression(expression)}


TOOLS: dict[str, ToolDefinition] = {
    "time": ToolDefinition(
        name="time",
        description="Return the current UTC date and time.",
        handler=time_tool,
    ),
    "calculator": ToolDefinition(
        name="calculator",
        description="Safely evaluate basic arithmetic expressions without executing arbitrary code.",
        handler=calculator_tool,
    ),
}


def list_tools() -> list[dict[str, str]]:
    return [{"name": tool.name, "description": tool.description} for tool in TOOLS.values()]


def tool_for_text(text: str) -> tuple[str, dict[str, Any]] | None:
    import re
    q = text.strip().lower()
    if q in {"time", "what time is it", "current time", "date today", "what is today"}:
        return "time", {}
    match = re.search(r"(?:calculate|what is)\s+([0-9pi e+\-*/().%]+)$", q)
    if not match:
        return None
    return "calculator", {"expression": match.group(1).replace(" ", "")}


def run_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    tool = TOOLS.get(name)
    if tool is None:
        raise KeyError(f"Unknown tool: {name}")
    return tool.handler(args)
