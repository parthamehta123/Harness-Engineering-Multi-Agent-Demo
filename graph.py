from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

from agents import (
    technical_agent,
    billing_agent,
    general_agent,
    reviewer_agent
)


TECHNICAL_WORDS = [
    "error", "bug", "login", "api", "install",
    "installation", "code", "server", "technical",
]
BILLING_WORDS = [
    "price", "pricing", "payment", "refund", "bill",
    "billing", "subscription", "plan", "charged",
]
GENERAL_WORDS = [
    "support team", "what can you", "what can your",
    "what do you", "who can help", "how can you help",
]

SPECIALISTS = {
    "technical": ("Technical Agent", technical_agent),
    "billing": ("Billing Agent", billing_agent),
    "general": ("General Agent", general_agent),
}


def detect_routes(question: str) -> list[str]:
    """Collect every matching specialist, not only the first hit."""
    text = question.lower()
    routes: list[str] = []

    if any(word in text for word in TECHNICAL_WORDS):
        routes.append("technical")
    if any(word in text for word in BILLING_WORDS):
        routes.append("billing")
    if any(phrase in text for phrase in GENERAL_WORDS):
        routes.append("general")

    if not routes:
        routes.append("general")

    return routes


class SupportState(TypedDict):
    question: str
    route: str
    draft: str
    final_answer: str
    blocked: bool
    trace: list[str]


def guardrail_node(state: SupportState):
    """
    A simple deterministic safety layer.
    In a real system this could include moderation,
    PII detection, permissions and policy checks.
    """
    question = state["question"].lower()
    dangerous_phrases = [
        "give me your password",
        "steal password",
        "full credit card number",
        "How to change or reset password?"
    ]

    blocked = any(phrase in question for phrase in dangerous_phrases)

    trace = state.get("trace", []) + ["Guardrail checked the request"]

    if blocked:
        return {
            "blocked": True,
            "final_answer": (
                "I can't help with requests involving passwords, stolen credentials, "
                "or full payment-card information."
            ),
            "trace": trace,
        }

    return {
        "blocked": False,
        "trace": trace,
    }


def after_guardrail(state: SupportState) -> Literal["router", "end"]:
    if state["blocked"]:
        return "end"
    return "router"




def router_node(state: SupportState):
    """
    We deliberately use deterministic routing for this beginner demo.

    Why?
    Production systems should not use an LLM for every decision.
    If a rule is simple and predictable, normal Python code is often
    cheaper, faster and easier to test.

    Mixed questions can match more than one specialist. The harness
    collects every match so billing policy is not invented by the
    technical agent.
    """
    routes = detect_routes(state["question"])
    route = " + ".join(routes)

    return {
        "route": route,
        "trace": state.get("trace", []) + [f"Router selected: {route}"],
    }


def specialists_node(state: SupportState):
    routes = [part.strip() for part in state["route"].split("+") if part.strip()]
    drafts = []
    trace = state.get("trace", [])

    for route in routes:
        label, agent = SPECIALISTS[route]
        drafts.append(f"[{label}]\n{agent(state['question'])}")
        trace = trace + [f"{label} created a draft"]

    return {
        "draft": "\n\n".join(drafts),
        "trace": trace,
    }


def reviewer_node(state: SupportState):
    final_answer = reviewer_agent(
        question=state["question"],
        draft=state["draft"],
    )
    return {
        "final_answer": final_answer,
        "trace": state.get("trace", []) + ["Reviewer Agent checked the answer"],
    }




builder = StateGraph(SupportState)

builder.add_node("guardrail", guardrail_node)
builder.add_node("router", router_node)
builder.add_node("specialists", specialists_node)
builder.add_node("reviewer", reviewer_node)

builder.add_edge(START, "guardrail")

builder.add_conditional_edges(
    "guardrail",
    after_guardrail,
    {
        "router": "router",
        "end": END,
    },
)

builder.add_edge("router", "specialists")
builder.add_edge("specialists", "reviewer")
builder.add_edge("reviewer", END)

support_graph = builder.compile()



def run_support_system(question: str):
    initial_state: SupportState = {
        "question": question,
        "route": "",
        "draft": "",
        "final_answer": "",
        "blocked": False,
        "trace": [],
    }

    result = support_graph.invoke(initial_state)

    return {
        "route": result.get("route", "blocked"),
        "answer": result["final_answer"],
        "trace": result.get("trace", []),
    }
