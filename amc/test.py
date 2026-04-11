from .decode import parse_packet, format_output


def run_self_test():
    test_hex = "1542A86C3287D9E58D896F187A8306F8D2520FBB5E9463349A473C224EBB99E7E9364A5B86CDA200D9"
    p = parse_packet(bytes.fromhex(test_hex))
    # Předáme DEBUG do format_output
    print(format_output(p, debug_mode=DEBUG))
    
    if p["decrypted"] and "Yenda" in p["decrypted"]["text"]:
        return True
    return False