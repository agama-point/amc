import asyncio
from datetime import datetime
from amc import Device, Decoder, DEVICE_ADDRESS, NAME_CHAR, RX_CHAR

# device: 0.1 | decoder: 0.1

CHANNELS = ["Public", "#test", "#praha", "#tech", "#freebeer"]
VERBOSE = True

async def notification_handler(sender, data):
    from amc.parser import format_forensic_output # Import pomocné funkce
    
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    res = decoder.decode(data)
    
    print(f"\n⌚ {ts} " + "="*60)
    print(format_forensic_output(res))
    print("-" * 75)

async def main():
    global decoder
    decoder = Decoder(CHANNELS)
    device = Device(DEVICE_ADDRESS, NAME_CHAR, RX_CHAR)

    print(f"--- MeshCore Monitor ---")
    print("[ver] device:", device.ver)
    print("[ver] decoder:", decoder.ver)
    try:
        if await device.connect():
            print(f"✅ CONNECTED: {device.name}")
            await device.start_monitoring(notification_handler)
            while True:
                await asyncio.sleep(1)
    finally:
        await device.disconnect()

if __name__ == "__main__":
    asyncio.run(main())


"""
(venv) PS D:\data_meshcore>
D:\data_meshcore>python d:/data_meshcore/amc_msg_raw.py                    

--- MeshCore Monitor ---
[ver] device: 0.1
[ver] decoder: 0.1
✅ CONNECTED: MeshCore-Yend@03

⌚ 11:17:03.499 ============================================================
        TYPE: MESH_PAYLOAD (Hops: 255)
        RAW : 88ff931d04720b220fb842e19bb551ca98309541a75c33725b8c75cf17c7b7fbd308921374c26cef45f94a0965318906ae76696c3bd98d6973bcfe2d
        DIV : HEADER:88 | HOPS_RAW:ff | SENDER:931d | DEST_HASH:0472 | SEQUENCE:0b
        DATA: 220fb842e19bb551ca98309541a75c33725b8c75cf17c7b7fbd308921374c26cef45f94a0965318906ae76696c3bd98d6973bcfe2d
        ASC : "..B...Q..0.A.\3r[.u.........t.l.E.J.e1...vil;..is..-
---------------------------------------------------------------------------

⌚ 11:17:04.006 ============================================================
        TYPE: MESH_PAYLOAD (Hops: 46)
        RAW : 882ecc1d05720b220fa8b842e19bb551ca98309541a75c33725b8c75cf17c7b7fbd308921374c26cef45f94a0965318906ae76696c3bd98d6973bcfe2d
        DIV : HEADER:88 | HOPS_RAW:2e | SENDER:cc1d | DEST_HASH:0572 | SEQUENCE:0b
        DATA: 220fa8b842e19bb551ca98309541a75c33725b8c75cf17c7b7fbd308921374c26cef45f94a0965318906ae76696c3bd98d6973bcfe2d
        ASC : "...B...Q..0.A.\3r[.u.........t.l.E.J.e1...vil;..is..-
---------------------------------------------------------------------------

⌚ 11:17:13.638 ============================================================
        TYPE: MESH_PAYLOAD (Hops: 19)
        RAW : 88139301048063510fb842edfc5ad8b7a2ff0dffb6ee40c85cfedbae73
        DIV : HEADER:88 | HOPS_RAW:13 | SENDER:9301 | DEST_HASH:0480 | SEQUENCE:63
        DATA: 510fb842edfc5ad8b7a2ff0dffb6ee40c85cfedbae73
        ASC : Q..B..Z........@.\...s
---------------------------------------------------------------------------
...

"""