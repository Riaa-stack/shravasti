import logging
from pydantic import BaseModel, Field

from app.core.config import settings
from app.agents.llm_client import get_llm
from app.agents.graph import ResearchState
from app.agents.prompts.chat_prompts import CHAT_PROMPT
from app.db.chroma import retrieve_chunks
from app.services.embeddings import get_embedding_model
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

class ChatOutput(BaseModel):
    response: str = Field(description="The final answer to the user's query")

async def run_chat(state: ResearchState) -> dict:
    query = state.get("query")
    if not query:
        raise ValueError("Chat agent requires a 'query' in the state.")
        
    logger.info(f"Running Chat Agent for query: {query}")
    
    # 1. Embed query
    embedding_model = get_embedding_model()
    query_embedding = embedding_model.encode(query).tolist()
    
    # 2. Retrieve top K chunks using the embedding
    chunks = retrieve_chunks(
        user_id=state["user_id"],
        paper_ids=state["paper_ids"],
        query_embedding=query_embedding,
        n_results=10
    )
    
    context = "\n\n".join([f"--- Source (Paper ID: {c['metadata'].get('paper_id')}, Page: {c['metadata'].get('page_number')}) ---\n{c['content']}" for c in chunks])
    
    # Extract sources for the output
    sources = [
        {
            "paper_id": c["metadata"].get("paper_id"),
            "page": c["metadata"].get("page_number"),
            "text_snippet": c["content"][:200] + "..."
        }
        for c in chunks
    ]
    
    # Format chat history
    history_str = ""
    for msg in state.get("chat_history", []):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_str += f"{role.capitalize()}: {content}\n"
        
    prompt = PromptTemplate(
        template=CHAT_PROMPT,
        input_variables=["context", "chat_history", "query"]
    )
    
    formatted_prompt = prompt.format(context=context, chat_history=history_str, query=query)
    
    llm = get_llm(settings.LLM_MODEL_CHAT)
    
    # For chat, we can just use the standard invoke and return a string
    result = await llm.ainvoke([HumanMessage(content=formatted_prompt)])
    
    return {
        "response": result.content,
        "sources": sources
    }
