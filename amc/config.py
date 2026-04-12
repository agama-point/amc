# Configuration for Agama MeshCore BLE connection
#y_03:
DEVICE_ADDRESS = "CE:2E:9F:xx:xx:xx"
#yTag:
#DEVICE_ADDRESS = "C6:04:19:D0:xx:xx"

# MeshCore (Nordic UART Service - NUS)
# 6e400002 = RX char  → App píše SEM   (write)
# 6e400003 = TX char  → App čte ODTUD  (notify)
RX_CHAR = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"   # ← oprava: 03 → 02
TX_CHAR = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"   # ← nové: pro notifikace

# Standard Device Name characteristic
NAME_CHAR = "00002a00-0000-1000-8000-00805f9b34fb"
