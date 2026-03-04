### Local Networks – Switch Implementation

## Requirements
Implementation of a network switch in Python (`switch.py`).

## Testing

Initialize the virtual topology and open one terminal for each host and one for each switch (terminals can be identified by their title):

```bash
sudo python3 checker/topo.py
```

### Manual Switch Startup

Run the switches manually from the switch terminal:

```bash
make run_switch SWITCH_ID=X
```

Where `X` is `0`, `1`, or `2` and represents the switch ID.

---

## Switching Table (CAM Table)

- A **HashMap** is used to associate each **MAC address** with a **port** (the path to that MAC).
- If the destination MAC address is **broadcast** (`ff:ff:ff:ff:ff:ff`), the frame is sent to **all ports except the one it was received on**.
- If the frame is not broadcast:
  - If the MAC address exists in the **CAM table**, the frame is forwarded only to the corresponding port.
  - If the MAC address is not found in the table, the frame is flooded to all ports except the ingress port.

---

## VLAN

- Another **HashMap** is used to store the VLAN type for each interface:
  - a VLAN ID for **access links**
  - `"T"` for **trunk links**

### Frame Processing

When receiving a frame:

- If it arrives on an **access link**, the VLAN ID is retrieved from the VLAN dictionary.
- If it arrives on a **trunk link**, the **802.1Q tag is removed** from the received frame.

When forwarding frames:

- The same forwarding logic from the **CAM table** is applied.
- If the frame is sent on a **trunk link**, an **802.1Q VLAN tag is added** before sending.

---

## STP (Spanning Tree Protocol)

An additional **HashMap** is used to store the **state of each port**.  
For simplicity, only two states are used:

- `listening`
- `blocking`

Root and designated ports are implicitly considered to be in the **listening** state.

### BPDU Transmission

The function `send_bpdu_every_second()` sends a **BPDU frame every second** to all **trunk ports**, but only if the current switch is the **root bridge**.

The BPDU frame contains:

- destination MAC address (the multicast address specified in the assignment)
- source MAC address (the switch MAC)
- `LLC_LENGTH`
- `LLC_HEADER` (DSAP, SSAP, control)
- BPDU header (Config BPDU size)
- BPDU configuration fields:
  - `flags = 0`
  - root bridge ID
  - root path cost
  - sender bridge ID
  - port ID

### BPDU Processing

When a BPDU frame is received (identified by its destination MAC):

1. The following values are extracted:
   - root bridge ID
   - sender path cost
   - sender bridge ID

2. If a **better root bridge** is discovered (lower priority):
   - all ports of the current switch move from **blocking** to **listening**, except the port connected to the new root bridge.

3. If the **root bridge ID remains the same**:
   - a lower-cost path to the root bridge is searched
   - port states are updated accordingly.

Finally:

- all **trunk ports of the root bridge** must remain in the **listening** state
- every time a frame is forwarded on a **trunk link**, the port state is checked to ensure it is **listening**
