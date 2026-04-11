# amc/parser.py

import io
import struct
# from datetime import datetime

class Decoder:
    def __init__(self, channel_names=None):
        self.ver = "0.1"
        self.channel_names = channel_names or ["Public"]
        # Zde doplň svůj 16-byte (32 hex znaků) klíč, pokud ho máš
        self.app_key = None # bytes.fromhex("00112233445566778899aabbccddeeff")

    def decode(self, data):
        if not data: return None
        
        cmd = data[0]
        res = {
            "type": self._get_type_name(cmd),
            "hops": data[1] if cmd == 0x88 else 0,
            "parts": {}, # Tady bude rozbitá struktura
            "raw_hex": data.hex(),
            "payload_data": b"",
            "decrypted": None
        }

        # --- DETAILNÍ ROZBOR PAKETU 0x88 ---
        if cmd == 0x88:
            # Předpokládaná struktura MeshCore Transport:
            # [Type 1B] [Hops 1B] [Sender 2B] [Dest 2B] [Seq 1B] [Payload...]
            try:
                res["parts"]["header"] = data[0:1].hex()
                res["parts"]["hops_raw"] = data[1:2].hex()
                res["parts"]["sender"] = data[2:4].hex()
                res["parts"]["dest_hash"] = data[4:6].hex()
                res["parts"]["sequence"] = data[6:7].hex()
                
                payload = data[7:]
                res["payload_data"] = payload
                
                # Pokus o dešifrování (pokud je klíč)
                if self.app_key and len(payload) > 4:
                    res["decrypted"] = self._attempt_decrypt(payload, res["parts"]["sender"])
            except Exception as e:
                res["error"] = f"Structure breakdown failed: {e}"

        return res

    def _get_type_name(self, cmd):
        types = {0x88: "MESH_PAYLOAD", 0x8A: "ADVERT", 0x08: "CHAN_MSG", 0x0C: "BATTERY"}
        return types.get(cmd, f"UNKNOWN(0x{cmd:02X})")

    def _attempt_decrypt(self, encrypted_data, sender_hex):
        # MeshCore často používá AES-CTR nebo ChaCha20
        # nonce bývá často složen z Sender ID + Sequence
        # TOTO JE MÍSTO PRO EXPERIMENTY S KRYPTOGRAFIÍ
        return "Not implemented - Key/IV unknown"

def format_forensic_output(res):
    """Vytvoří extrémně ukecaný výstup pro terminál."""
    if not res: return "Empty data"

    out = [
        f"        TYPE: {res['type']} (Hops: {res['hops']})",
        f"        RAW : {res['raw_hex']}"
    ]
    
    if res['parts']:
        parts_str = " | ".join([f"{k.upper()}:{v}" for k, v in res['parts'].items()])
        out.append(f"        DIV : {parts_str}")
    
    if res['payload_data']:
        # Vypíše payload jako hex a zkusí ASCII "náhled"
        p_hex = res['payload_data'].hex()
        p_asc = "".join([chr(b) if 32 <= b <= 126 else "." for b in res['payload_data']])
        out.append(f"        DATA: {p_hex}")
        out.append(f"        ASC : {p_asc}")

    if res['decrypted']:
        out.append(f"        DECR: {res['decrypted']}")
        
    return "\n".join(out)