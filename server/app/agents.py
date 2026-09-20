from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDecision:
    name: str
    instruction: str


AGENTS = {
    "study": AgentDecision("study", "Explain concepts clearly, prioritize exam-ready definitions, examples, steps, and key points."),
    "pdf": AgentDecision("pdf", "Ground the answer in the supplied document retrieval and cite page numbers when available. Never invent sources."),
    "quiz": AgentDecision("quiz", "Create useful practice questions and explanations appropriate for a university student."),
    "planner": AgentDecision("planner", "Help organize realistic study tasks, priorities, topics, and time blocks."),
    "coding": AgentDecision("coding", "Act as a coding tutor: explain the approach, provide correct code, and mention important edge cases."),
    "general": AgentDecision("general", "Answer helpfully and concisely while staying focused on the user's request."),
}


def route_agent(question: str, task: str = "answer", document_id: str | None = None) -> AgentDecision:
    """Choose a lightweight JARVIS agent without requiring a second model call."""
    if document_id:
        return AGENTS["pdf"]

    q = question.lower()
    if task == "quiz" or any(x in q for x in ("quiz", "mcq", "multiple choice", "test me")):
        return AGENTS["quiz"]
    if task in {"summary", "notes", "flashcards"} or any(x in q for x in ("study", "exam", "explain", "summarize", "notes", "flashcard")):
        return AGENTS["study"]
    if any(x in q for x in ("plan my", "study plan", "timetable", "schedule", "planner")):
        return AGENTS["planner"]
    if any(x in q for x in ("python", "java", "javascript", "typescript", "code", "debug", "leetcode", "algorithm", "program")):
        return AGENTS["coding"]
    return AGENTS["general"]
