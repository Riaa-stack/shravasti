from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
import logging

logger = logging.getLogger(__name__)

class ResearchState(TypedDict):
    user_id: str
    paper_ids: list[str]
    task_type: str  # literature_review | methodology | gap | trend | idea | citation | chat | difficulty
    query: str | None
    chat_history: list[dict] | None
    retrieved_chunks: list[dict]
    result: dict

def router_node(state: ResearchState) -> str:
    """Routes the state to the appropriate agent based on task_type."""
    task_map = {
        "literature_review": "literature_review_agent",
        "methodology": "methodology_agent",
        "gap": "research_gap_agent",
        "trend": "trend_agent",
        "idea": "idea_agent",
        "citation": "citation_agent",
        "chat": "chat_agent",
        "difficulty": "difficulty_agent"
    }
    target = task_map.get(state["task_type"])
    if not target:
        raise ValueError(f"Unknown task_type: {state['task_type']}")
    return target

# --- Placeholder Agent Nodes (to be replaced by actual imports later) ---

async def literature_review_agent(state: ResearchState) -> dict:
    from app.agents.literature_review_agent import run_literature_review
    state["result"] = await run_literature_review(state)
    return state

async def methodology_agent(state: ResearchState) -> dict:
    from app.agents.methodology_agent import run_methodology_analysis
    state["result"] = await run_methodology_analysis(state)
    return state

async def research_gap_agent(state: ResearchState) -> dict:
    from app.agents.research_gap_agent import run_research_gap_detection
    state["result"] = await run_research_gap_detection(state)
    return state

async def trend_agent(state: ResearchState) -> dict:
    from app.agents.trend_agent import run_trend_analysis
    state["result"] = await run_trend_analysis(state)
    return state

async def idea_agent(state: ResearchState) -> dict:
    from app.agents.idea_agent import run_idea_generation
    state["result"] = await run_idea_generation(state)
    return state

async def citation_agent(state: ResearchState) -> dict:
    from app.agents.citation_agent import run_citation_generation
    state["result"] = await run_citation_generation(state)
    return state

async def chat_agent(state: ResearchState) -> dict:
    from app.agents.chat_agent import run_chat
    state["result"] = await run_chat(state)
    return state

async def difficulty_agent(state: ResearchState) -> dict:
    from app.agents.difficulty_agent import run_difficulty_prediction
    state["result"] = await run_difficulty_prediction(state)
    return state

# --- Build the Graph ---

workflow = StateGraph(ResearchState)

workflow.add_node("literature_review_agent", literature_review_agent)
workflow.add_node("methodology_agent", methodology_agent)
workflow.add_node("research_gap_agent", research_gap_agent)
workflow.add_node("trend_agent", trend_agent)
workflow.add_node("idea_agent", idea_agent)
workflow.add_node("citation_agent", citation_agent)
workflow.add_node("chat_agent", chat_agent)
workflow.add_node("difficulty_agent", difficulty_agent)

workflow.set_conditional_entry_point(
    router_node,
    {
        "literature_review_agent": "literature_review_agent",
        "methodology_agent": "methodology_agent",
        "research_gap_agent": "research_gap_agent",
        "trend_agent": "trend_agent",
        "idea_agent": "idea_agent",
        "citation_agent": "citation_agent",
        "chat_agent": "chat_agent",
        "difficulty_agent": "difficulty_agent",
    }
)

workflow.add_edge("literature_review_agent", END)
workflow.add_edge("methodology_agent", END)
workflow.add_edge("research_gap_agent", END)
workflow.add_edge("trend_agent", END)
workflow.add_edge("idea_agent", END)
workflow.add_edge("citation_agent", END)
workflow.add_edge("chat_agent", END)
workflow.add_edge("difficulty_agent", END)

research_graph = workflow.compile()
