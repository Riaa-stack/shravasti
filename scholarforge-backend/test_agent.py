import asyncio
import logging
from unittest.mock import patch
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from app.agents.graph import ResearchState
from app.agents.literature_review_agent import run_literature_review

# Setup logging
logging.basicConfig(level=logging.INFO)

# Mocked output for the retrieve_chunks function
MOCK_CHUNKS = [
    {
        "content": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
        "metadata": {"paper_id": "transformer_1", "page_number": 1}
    },
    {
        "content": "Experiments on two machine translation tasks show these models to be superior in quality while being significantly more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task.",
        "metadata": {"paper_id": "transformer_1", "page_number": 2}
    }
]

async def test_literature_review():
    print("\n--- Starting Agent Test ---")
    
    # 1. Create a mock state for the agent
    mock_state: ResearchState = {
        "user_id": "test_user",
        "paper_ids": ["transformer_1"],
        "task_type": "literature_review",
        "query": None,
        "chat_history": None,
        "retrieved_chunks": [],
        "result": {}
    }
    
    # 2. Patch the ChromaDB retrieval function so it doesn't try to connect to the DB
    with patch("app.agents.literature_review_agent.retrieve_chunks") as mock_retrieve:
        mock_retrieve.return_value = MOCK_CHUNKS
        
        print("Running the literature review agent. This will call the OpenAI API...\n")
        
        # 3. Run the agent
        try:
            result = await run_literature_review(mock_state)
            
            print("\n--- Agent Result (Structured Output) ---")
            import json
            print(json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"\n[ERROR] The agent failed: {e}")
            print("Did you make sure to put a valid OPENROUTER_API_KEY in your .env file?")

if __name__ == "__main__":
    asyncio.run(test_literature_review())
