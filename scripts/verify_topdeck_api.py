import os
import logging
from dotenv import load_dotenv
from src.services.topdeck import TopDeckService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_verify")

def verify():
    load_dotenv()
    api_key = os.getenv("TOPDECK_API_KEY")
    api_url = os.getenv("TOPDECK_API_URL", "https://topdeck.gg/api")
    
    if not api_key:
        logger.error("TOPDECK_API_KEY not found in .env")
        return

    logger.info(f"Testing TopDeck API with URL: {api_url}")
    service = TopDeckService(api_key=api_key, api_url=api_url)
    
    # Test 1: Get active tournaments
    logger.info("Testing get_active_tournaments...")
    tournaments = service.get_active_tournaments()
    if tournaments:
        logger.info(f"Successfully fetched {len(tournaments)} tournaments.")
        if len(tournaments) > 0:
            first_tid = tournaments[0].get('id')
            logger.info(f"First tournament ID: {first_tid}")
            
            # Test 2: Get tournament details
            logger.info(f"Testing get_tournament_details for {first_tid}...")
            details = service.get_tournament_details(first_tid)
            if details:
                logger.info(f"Successfully fetched details for {first_tid}: {details.get('name')}")
                
                # Test 3: Get standings
                logger.info(f"Testing get_standings for {first_tid}...")
                standings = service.get_standings(first_tid)
                if standings:
                    logger.info("Successfully fetched standings.")
                else:
                    logger.warning("Failed to fetch standings.")
            else:
                logger.error(f"Failed to fetch details for {first_tid}")
        else:
            logger.warning("No tournaments found in the response.")
    else:
        logger.error("Failed to fetch active tournaments.")

if __name__ == "__main__":
    verify()
