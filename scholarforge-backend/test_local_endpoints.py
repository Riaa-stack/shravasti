import httpx
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_endpoints():
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient(base_url=base_url) as client:
        logger.info("Testing /health endpoint...")
        try:
            response = await client.get("/health")
            logger.info(f"Health Check Status: {response.status_code}")
            logger.info(f"Health Check Response: {response.json()}")
        except Exception as e:
            logger.error(f"Failed to reach /health: {e}")
            return
            
        logger.info("\nTesting missing route...")
        try:
            response = await client.get("/api/v1/invalid")
            logger.info(f"Invalid Route Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed invalid route test: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoints())
