from langchain_openai import ChatOpenAI
from app.core.config import settings


def get_llm(
    model_name: str,
    temperature: float = 0.0
) -> ChatOpenAI:
    """
    Returns a LangChain ChatModel configured to use OpenRouter.

    OpenRouter provides an OpenAI-compatible API, so ChatOpenAI
    is used as the LangChain client.
    """

    return ChatOpenAI(
        openai_api_key=settings.OPENROUTER_API_KEY,  # type: ignore
        openai_api_base=settings.OPENROUTER_BASE_URL,
        model_name=model_name,
        temperature=temperature,

        # Keep this below the remaining OpenRouter credit limit.
        max_tokens=3000,

        default_headers={
            "HTTP-Referer": "https://github.com/scholarforge/scholarforge",
            "X-Title": "ScholarForge AI",
        },
    )