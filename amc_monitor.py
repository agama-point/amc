#!/usr/bin/env python3
# AgamaPoint MeshCore monitor | amc_monitor.py

import asyncio
from amc.decode import parse_packet, format_output, print_knowledge_base
from amc.test import run_self_test
# from amc.decode import MSG_ONLY, DEDUP_WINDOW
import amc.decode as mcd
from amc import Device, DEVICE_ADDRESS, NAME_CHAR, RX_CHAR, TX_CHAR
import os
from datetime import datetime

DEBUG = False
DATA_LOG = True
mcd.MSG_ONLY = True
mcd.DEDUP_WINDOW = 2.0

print_knowledge_base()

# -------------- log ---------------
filename = datetime.now().strftime("data/msg_log_%y%m%d_%H%M.txt")
if DATA_LOG:
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("amc_monitor | data log\n")


def log_str(s):
    if not DATA_LOG or filename is None:
        return

    with open(filename, 'a', encoding='utf-8') as f:
        f.write(s + "\n")
# -------------- /log ---------------


async def main():
    # 1. Run self-test if DEBUG is enabled (set in amc/test.py)
    if DEBUG:
        if not run_self_test():
            print("❌ Self-test failed. Exiting.")
            return

    print(f"🔍 Searching for device {DEVICE_ADDRESS}...")
    dev = Device(DEVICE_ADDRESS, NAME_CHAR, RX_CHAR, tx_char=TX_CHAR)
    
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
                  if DATA_LOG:
                      log_str(out)

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
✅ Connected. Device name: [ MeshCore-Yend@03 ]
===============================================================
Monitoring traffic...

10:49:30.078 | 88 | 72B | 30D0 ➔ 1540 | CHAN MSG
  [#tech] Yenda_Tag: Hlásím funkční py.monitor, light verze
10:51:10.008 | 88 | 56B | 2ECF ➔ 1540 | CHAN MSG
  [#freebeer] Yenda_Tag: BEER! Na oslavu amc_monitor
10:51:53.749 | 88 | 72B | 2FCF ➔ 1540 | CHAN MSG
  [#2byte] Yenda_Tag: Mám nastaveno 2B, zkouknu trasy. 
14:52:12.437 | 88 | 40B | 2FE5 ➔ 1540 | CHAN MSG
  [#freebeer] Yenda_Tag: BEER! A zima
14:53:57.681 | 88 | 112B | FE8E ➔ 1508 | CHAN MSG
  [#2byte] Lȑ{
14:59:20.511 | 88 | 40B | 30E4 ➔ 1540 | CHAN MSG
  [#test] Yenda_Tag: Test monitor
14:59:31.133 | 88 | 74B | 0990 ➔ 1541 | CHAN MSG
  [#test] EL Pong: @[Yenda_Tag] Test OK, přijato: "Test monitor".
14:59:50.271 | 88 | 76B | 30CB ➔ 1504 | CHAN MSG
  [#test] agoranode: @[Yenda_Tag] podej žákovskou, píši za 1
15:00:15.203 | 88 | 74B | FF8F ➔ 1502 | CHAN MSG
  [#test] agoranode: @[EL Pong] podej žákovskou, píši za 1
15:00:39.323 | 88 | 46B | 058F ➔ 1506 | CHAN MSG
  [Public] Dejv Bobry mobile: (*Bobry)
...
"""