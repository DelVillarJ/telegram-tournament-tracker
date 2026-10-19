import os
from dotenv import load_dotenv
from src.services.topdeck import TopDeckService
import json

def test_topdeck_api():
    load_dotenv()
    
    api_key = os.getenv("TOPDECK_CLIENT_SECRET")
    api_url = os.getenv("TOPDECK_API_URL", "https://topdeck.gg/api")
    
    if not api_key:
        print("Error: TOPDECK_CLIENT_SECRET not found in .env")
        return

    print(f"Testing TopDeck API with URL: {api_url}")
    service = TopDeckService(api_key=api_key, api_url=api_url)
    
    print("Fetching active tournaments...")
    tournaments = service.get_active_tournaments()
    
    if tournaments is not None:
        print(f"Successfully fetched {len(tournaments)} tournaments.")
        print(json.dumps(tournaments, indent=2))
    else:
        print("Failed to fetch tournaments (returned None).")

if __name__ == "__main__":
    test_topdeck_api()
