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
              parsed = parse_packet(bytes(data))
              out = format_output(parsed, debug_mode=DEBUG)
              if out is not None:
                  print(out)
                        
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

   AMC | AGAMA_POINT MESHCORE GRP_TXT DECODER 
   ==========================================
   Algorithm: AES-128 ECB
   Key:       SHA256(channel_name)[:16]
   Struct.:   [header][path_len][path(4B)][ch_hash(3B)][enc(26B)][mac(6B)]
   Plaintext: [timestamp(4B LE)][0x00][text...]
   ------------------------------------------------
   Info:
   
   ver:  0.33 | 2026-03
===============================================================
🔍 Searching for device CE:2E:9F:5E:12:FB...
===============================================================

   AMC | AGAMA_POINT MESHCORE GRP_TXT DECODER 
   ==========================================
   Algorithm: AES-128 ECB
   Key:       SHA256(channel_name)[:16]
   Struct.:   [header][path_len][path(4B)][ch_hash(3B)][enc(26B)][mac(6B)]
   Plaintext: [timestamp(4B LE)][0x00][text...]
   ------------------------------------------------
   Info:
   
   ver:  0.33 | 2026-03
===============================================================
✅ Connected. Device name: [ MeshCore-Yend@03 ]
===============================================================
Monitoring traffic...

10:49:30.078 | 88 | 72B | 30D0 ➔ 1540 | CHAN MSG
  [#tech] Yenda_Tag: Hlásím funkční py.monitor, light verze
10:51:10.008 | 88 | 56B | 2ECF ➔ 1540 | CHAN MSG
  [#freebeer] Yenda_Tag: BEER! Na oslavu amc_monitor
10:51:53.749 | 88 | 72B | 2FCF ➔ 1540 | CHAN MSG
  [#2byte] Yenda_Tag: Mám nastaveno 2B, zkouknu trasy. 
10:54:08.389 | 88 | 40B | 2FD1 ➔ 1540 | CHAN MSG
  [#test] Yenda_Tag: Test
10:55:38.031 | 88 | 40B | 30E8 ➔ 1540 | CHAN MSG
  [#test] Yenda_Tag: Test 123
10:55:49.072 | 88 | 74B | 0E91 ➔ 1541 | CHAN MSG
  [#test] EL Pong: @[Yenda_Tag] Funguje to perfektně, Yenda_Tag!
...
"""