#!/usr/bin/env python3
"""
amc_send.py - tests amc/send.py
Device connection is handled here, sending logic is in amc/send.py
"""

import asyncio
from amc import DEVICE_ADDRESS, NAME_CHAR, RX_CHAR
from amc.device import Device
from amc.send import send_channel_msg

# --- config: test MSG ---
DEBUG   = False
CHANNEL = "#test"
MESSAGE = "Test 2 from desktop Lib."
# --------------

async def main():
    print("=" * 55)
    print(f"  amc_send.py")
    print(f"  DEBUG   = {DEBUG}")
    print("=" * 55)
    print(f"  Device  : {DEVICE_ADDRESS}")
    print(f"  Channel : {CHANNEL}")
    print(f"  Message : \"{MESSAGE}\"")
    print("=" * 55)

    # -- Connection --
    print(f"\n{'-'*55}")
    print(f"  ◆ CONNECTING")
    print(f"{'-'*55}")
    dev = Device(DEVICE_ADDRESS, NAME_CHAR, RX_CHAR)
    print(f"  Connecting to {DEVICE_ADDRESS}...")
    try:
        await dev.connect()
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return

    print(f"  ✅ Connected. Device: \033[92m[ {dev.name} ]\033[0m")

    # -- Sending --
    try:
        ok = await send_channel_msg(
            dev     = dev,
            channel = CHANNEL,
            message = MESSAGE,
            debug   = DEBUG,
        )
    finally:
        # -- Disconnect --
        print(f"\n{'-'*55}")
        print(f"  ◆ DISCONNECTING")
        print(f"{'-'*55}")
        await dev.disconnect()
        print(f"  🔌 Disconnected.")
        print()

    if not ok:
        print("Test FAILED.")
        exit(1)
    print("Test OK.")


if __name__ == "__main__":
    asyncio.run(main())