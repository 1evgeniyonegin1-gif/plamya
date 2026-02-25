"""Example: running an autonomous agent with PLAMYA Heartbeat."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.heartbeat import Heartbeat
from actions.study_products import study_products
from actions.read_channel import read_channel


async def main():
    hb = Heartbeat()

    # Register autonomous tasks
    hb.register("chappie", "study_products", interval_minutes=120, callback=study_products)
    hb.register("chappie", "read_channels", interval_minutes=30, callback=read_channel)

    print("Chappie agent started. Press Ctrl+C to stop.")
    try:
        await hb.run_forever()
    except KeyboardInterrupt:
        hb.stop()
        print("Chappie agent stopped.")


if __name__ == "__main__":
    asyncio.run(main())
