"""Quick test — hit Scraper Tech with a small query and print parsed results."""
import asyncio
import json

from app.pipeline.discovery import fetch_google_maps_leads


async def main():
    results = await fetch_google_maps_leads("hvac in texas", limit=3)
    print(f"\nGot {len(results)} businesses:\n")
    for biz in results:
        print(json.dumps(biz, indent=2, default=str))
        print("---")


if __name__ == "__main__":
    asyncio.run(main())
