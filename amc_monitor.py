#!/usr/bin/env python3

import asyncio
from amc.decode import parse_packet, format_output
from amc.test import run_self_test
from amc import Device, DEVICE_ADDRESS, NAME_CHAR, RX_CHAR

DEBUG = False


async def main():
    # 1. Spustit test pokud je DEBUG aktivní (nastavuješ v amc/test.py)
    if DEBUG:
        if not run_self_test():
            print("❌ Self-test failed. Exiting.")
            return

    print(f"🔍 Searching for device {DEVICE_ADDRESS}...")
    dev = Device(DEVICE_ADDRESS, NAME_CHAR, RX_CHAR)
    
    try:
        if await dev.connect():
            print("✅ Connected. Monitoring traffic...\n")
            
            # --- TADY JE TEN HANDLER ---
            async def handler(sender, data):
                # Převedeme data na bytes, parsujeme a zformátujeme s ohledem na DEBUG
                parsed = parse_packet(bytes(data))
                # format_output teď dostává druhý parametr 'debug_mode'
                print(format_output(parsed, debug_mode=DEBUG))
            
            # Registrace handleru do BLE knihovny
            await dev.start_monitoring(handler)
            
            # Udržujeme smyčku naživu
            while True:
                await asyncio.sleep(1)
        else:
            print("❌ Could not connect.")
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        await dev.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Monitor terminated by user.")

"""
...[#test] Yenda_Tag: Test pro geminy3
19:02:50.599 | 88 | 44B | 1092 ➔ 1542
19:02:50.718 | 88 | 46B | 2ECC ➔ 1543
19:02:51.708 | 88 | 48B | E587 ➔ 1544
19:02:53.811 | 88 | 110B | 1193 ➔ 154B
19:02:54.740 | 88 | 112B | 31CD ➔ 154C
19:03:05.811 | 88 | 63B | 1593 ➔ 1D07
19:03:06.018 | 88 | 60B | E587 ➔ 1D04
19:03:06.708 | 88 | 64B | 33CD ➔ 1D08
19:03:08.118 | 88 | 74B | 0F92 ➔ 1502
  [#test] agoranode: @[Yenda_Tag] podej žákovskou, píši za 1
...
"""