"""
Test the owner identification waterfall.

Usage:
    uv run --no-env-file python -m scripts.test_owner_id
"""
import asyncio
from app.pipeline.owner_id import identify_owner


TESTS = [
    ("North Texas HVAC", "https://www.northtxhvac.com/", "Roanoke", "TX", "Bryan Slagle"),
    ("HVAC of Texas", "http://hvacoftexas.org/", "Pipe Creek", "TX", "Daniel Tuma"),
    ("Texas HVAC Repair", "https://txhvacrepair.com/", "Arlington", "TX", "Unknown"),
]


async def main():
    print("=" * 70)
    print("Owner Identification Waterfall Test")
    print("=" * 70)

    for biz_name, website, city, state, expected in TESTS:
        name, source = await identify_owner(website, biz_name, city, state)

        print(f"\n  {biz_name} ({city}, {state})")
        print(f"  Expected: {expected}")
        print(f"  Found:    {name or 'not found'}")
        print(f"  Source:   {source or 'n/a'}")


if __name__ == "__main__":
    asyncio.run(main())
