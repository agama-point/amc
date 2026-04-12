#!/usr/bin/env python3
# AgamaPoint MeshCore monitor | amc_monitor.py

import asyncio
from amc.decode import parse_packet, format_output, print_knowledge_base
from amc.test import run_self_test
from amc import Device, DEVICE_ADDRESS, NAME_CHAR, RX_CHAR

DEBUG = False

print_knowledge_base()


async def main():
    # 1. Run self-test if DEBUG is enabled (set in amc/test.py)
    if DEBUG:
        if not run_self_test():
            print("❌ Self-test failed. Exiting.")
            return

    print(f"🔍 Searching for device {DEVICE_ADDRESS}...")
    dev = Device(DEVICE_ADDRESS, NAME_CHAR, RX_CHAR)
    
    try:
        if await dev.connect():
            print_knowledge_base()
            print(f"✅ Connected. Device name: \033[92m[ {dev.name} ]\033[0m")
            print("="*63)
            print("Monitoring traffic...\n")
            
            # --- HERE IS THE HANDLER ---
            async def handler(sender, data):
                # Convert data to bytes, parse, and format with respect to DEBUG
                parsed = parse_packet(bytes(data))
                # format_output now receives the second parameter 'debug_mode'
                print(format_output(parsed, debug_mode=DEBUG))
            
            # Register handler in BLE library
            await dev.start_monitoring(handler)
            
            # Keep the loop alive
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
===============================================================
🔍 Searching for device CE:2E:9F:5E:12:FB...
===============================================================

   MESHCORE GRP_TXT DECODER 
   ========================
   Algorithm: AES-128 ECB
   Key:       SHA256(channel_name)[:16]
   Struct.:   [header][path_len][path(4B)][ch_hash(3B)][enc(26B)][mac(6B)]
   Plaintext: [timestamp(4B LE)][0x00][text...]
   ------------------------------------------------
   Info:
   
   ver:  0.2|2026-03
===============================================================
✅ Connected. Device name: [ MeshCore-Yend@03 ]
===============================================================
Monitoring traffic...

09:13:14.386 | 88 | 40B | 30D2 ➔ 1540
  [#test] Yenda_Tag: Test dobré rano
09:13:14.595 | 88 | 42B | 30C9 ➔ 1541
  [#test] Yenda_Tag: Test dobré rano
09:13:15.374 | 88 | 46B | 068F ➔ 1543
  [#test] Yenda_Tag: Test dobré rano
09:13:23.177 | 88 | 74B | 048E ➔ 1541
  [#test] EL Pong: @[Yenda_Tag] Funguje, dobré ráno i tobě!
09:13:23.595 | 88 | 76B | 32CA ➔ 1542
  [#test] EL Pong: @[Yenda_Tag] Funguje, dobré ráno i tobě!
09:13:37.636 | 88 | 40B | 32D2 ➔ 1540
  [#test] Yenda_Tag: Ping
09:13:38.054 | 88 | 42B | 33CA ➔ 1541
  [#test] Yenda_Tag: Ping
09:13:38.475 | 88 | 44B | 048F ➔ 1542
  [#test] Yenda_Tag: Ping
09:13:42.677 | 88 | 59B | DB85 ➔ 1503
  [#test] Luky-HomeAssistant: Yenda_Tag Pong
09:13:42.677 | 83 | 1B
09:13:42.885 | 88 | 60B | 2DC9 ➔ 1504
  [#test] Luky-HomeAssistant: Yenda_Tag Pong
09:13:43.275 | 88 | 59B | F38D ➔ 1503
  [#test] Luky-HomeAssistant: Yenda_Tag Pong
09:13:43.935 | 88 | 75B | 028E ➔ 1503
  [#test] agoranode: @[Yenda_Tag] podej žákovskou, píši za 1
09:13:43.935 | 83 | 1B
09:13:44.775 | 88 | 76B | 33CA ➔ 1504
  [#test] agoranode: @[Yenda_Tag] podej žákovskou, píši za 1
09:13:48.407 | 88 | 79B | E085 ➔ 1507
  [#test] observer.hkfree.org: Hradec Kralove OK, Yenda_Tag
...
"""