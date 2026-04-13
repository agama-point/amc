# Agama MeshCore BLE Tools


Experimental Python tools for interacting with **Agama MeshCore** devices over Bluetooth Low Energy (BLE).


## Install
```bash
git clone https://github.com/agama-point/amc.git
cd amc
python3 -m venv venv  
source venv/bin/activate
pip install -r requirements.txt
```

---

## Overview


This repository contains simple utilities for:



- Scanning nearby BLE devices
- Connecting to a specific device
- Reading device information (e.g. name, services, characteristics)
- Low-level reading and sending of BLE messages (MeshCore communication)


The goal is to explore and better understand MeshCore communication at a low level.


## Project Structure


- `amc_config.py`  

&#x20; Configuration file (device address, UUIDs, etc.)

- `amc_ble_list.py`  

&#x20; Scan nearby BLE devices

- `amc_connect.py`  

&#x20; Connects to a device and prints its services and characteristics

- `amc_comm.py` *(planned / included)*  

&#x20; Low-level communication tool for reading and sending messages



## Status

⚠️ This is an **experimental project**.  

Functionality may change, break, or be incomplete.



## Platform Support

- ✅ **Windows** — works best (due to BLE library support)
- ⚠️ **Linux** — partial / in progress

Improving Linux compatibility is planned.

---
## Requirements

- Python 3.10+

Install dependencies:

```bash
pip install -r requirements.txt
```

---

[AMC specification](https://github.com/agama-point/amc/blob/main/amc_spec.md)

[flasher](https://meshcore.co.uk/flasher.html)
| on-line app: [app.meshcore.nz](https://app.meshcore.nz/)



