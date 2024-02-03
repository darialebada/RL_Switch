#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

own_bridge_id = 0
root_bridge_id = 0
interfaces = 0
root_path_cost = 0
sender_bridge_id = 0
sender_cost_path = 0
# hashmap to know interface-vlan
vlan = {}

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def send_bdpu_every_sec():
    global own_bridge_id
    global root_bridge_id
    global interfaces
    global sender_bridge_id
    global sender_cost_path
    global vlan

    bpdu_length = 44

    while True:
        # TODO Send BDPU every second if necessary
        # check if switch is root
        if own_bridge_id == root_bridge_id:
            for i in interfaces:
                # send BPDU to all trunk ports
                if vlan[get_interface_name(i)] == "T":
                    # destination MAC 
                    dest = "01:80:c2:00:00:00"
                    dst = bytes.fromhex(dest.replace(":", ""))
                    # source MAC is switch MAC
                    src = get_switch_mac()            
                    # packet length
                    llc_length = bpdu_length.to_bytes(2, byteorder='big')
                    dsap = 0x42
                    ssap = 0x42
                    control = 0x03
                    llc_header = dsap.to_bytes(1, byteorder='big') + ssap.to_bytes(1, byteorder='big') + control.to_bytes(1, byteorder='big')
                    # bpdu header length
                    bpdu_header = 23
                    bpdu_header = bpdu_header.to_bytes(4, byteorder='big')
                    # uint8_t root_bridge_id[8]
                    root_bridge_bytes = own_bridge_id.to_bytes(8, byteorder='big')
                    # uint32_t root_path_cost
                    root_path_bytes = sender_cost_path.to_bytes(4, byteorder='big')
                    # uint8_t bridge_id[8]
                    sender_bridge_bytes = own_bridge_id.to_bytes(8, byteorder='big')
                    # uint16_t port_id
                    port_id = i.to_bytes(2, byteorder='big')

                    # get data to send
                    bpdu_data = dst + src + llc_length + llc_header + bpdu_header + bytes([0]) + root_bridge_bytes + root_path_bytes + sender_bridge_bytes + port_id
                    # send acket to trunk port
                    send_to_link(i, bpdu_data, bpdu_length)
        time.sleep(1)

def main():
    global own_bridge_id
    global root_bridge_id
    global root_path_cost
    global interfaces
    global sender_bridge_id
    global sender_cost_path
    global vlan

    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    # open switch config file
    file_name = r"configs/switch" + str(switch_id) + ".cfg"
    file = open(file_name, "r")
    lines = file.readlines()
    count = 0

    # know vlan for each port
    for i in interfaces:
        for line in lines:
            if count == 0:
                # bridge id == priority in our case
                priority = int(line.split()[0])
                count = 1
            elif get_interface_name(i) == line.split()[0]:
               vlan[get_interface_name(i)] = line.split()[1]

    file.close()

    port_state = {}
    
    # init each port state
    for i in interfaces:
        if vlan[get_interface_name(i)] == "T":
            port_state[get_interface_name(i)] = "BLOCKING"
        else:
            port_state[get_interface_name(i)] = "LISTENING"
    
    # init for stp
    own_bridge_id = priority
    root_bridge_id = own_bridge_id
    root_path_cost = 0

    # check root bridge
    if own_bridge_id == root_bridge_id:
        for i in interfaces:
            if vlan[get_interface_name(i)] == "T":
                port_state[get_interface_name(i)] = "LISTENING"

    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()

    # Printing interface names
    for i in interfaces:
        print(get_interface_name(i))

    # declare MAC table null
    MAC_table = {}

    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        # check for BPDU packet
        dest_check = ':'.join(f'{b:02x}' for b in data[0:6])
        if dest_check == "01:80:c2:00:00:00":
            # get data from BPDU packet
            dest_mac = ':'.join(f'{b:02x}' for b in data[0:6])
            src_mac = ':'.join(f'{b:02x}' for b in data[6:12])

            root_bridge_bpdu = int.from_bytes(data[22:30], byteorder='big')
            sender_cost_bpdu = int.from_bytes(data[30:34], byteorder='big')
            sender_bridge_id = int.from_bytes(data[34:42], byteorder='big')
            
            # check if we need to change root port (smaller priority value)
            if root_bridge_bpdu < root_bridge_id:
                root_path_cost = sender_cost_bpdu + 10
                root_port = interface
                # change root bridge => block ports
                if root_bridge_id == own_bridge_id:
                    for i in interfaces:
                        if vlan[get_interface_name(i)] == "T":
                            if i == root_port:
                                # port opposite of root bridge => must be designated (listening)
                                port_state[get_interface_name(root_port)] = "LISTENING"
                            else:
                                port_state[get_interface_name(i)] = "BLOCKING"
                # change root bridge
                root_bridge_id = root_bridge_bpdu

                # change data to send packet again (after 1 second)
                sender_bridge_id = own_bridge_id
                sender_cost_path = root_path_cost
            # same root port
            elif root_bridge_id == root_bridge_bpdu:
                # new path to root (less cost)
                if interface == root_port and sender_cost_bpdu + 10 < root_path_cost:
                        root_path_cost = sender_cost_bpdu + 10
                elif interface != root_port:
                    # check if route to root bridge is throught this switch
                    if sender_cost_bpdu > root_path_cost:
                        port_state[get_interface_name(interface)] = "LISTENING"
            elif sender_bridge_id == own_bridge_id:
                port_state[get_interface_name(interface)] = "BLOCKING"

            # change root bridge ports to designated
            if own_bridge_id == root_bridge_id:
                for i in interfaces:
                    if vlan[get_interface_name(i)] == "T":
                        port_state[get_interface_name(i)] = "LISTENING"

            continue


        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')

        print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        # TODO: Implement forwarding with learning
        # TODO: Implement VLAN support
        # TODO: Implement STP support

        if vlan_id == -1:
            # access link => get vlan
            vlan_id = int(vlan[get_interface_name(interface)])
        else:
            # trunk link => get data without tag
            data = data[0:12] + data[16:]
            length -= 4 

        MAC_table[src_mac] = interface
        if dest_mac != "ff:ff:ff:ff:ff:ff":
            if dest_mac in MAC_table:
                # dest_mac in in CAM table => we know where to send (check vlan)
                if vlan[get_interface_name(MAC_table[dest_mac])] == "T":
                    # trunk link => add tag
                    if port_state[get_interface_name(MAC_table[dest_mac])] == "LISTENING":
                        data_tag = data[0:12] + create_vlan_tag(vlan_id) + data[12:]
                        send_to_link(MAC_table[dest_mac], data_tag, length + 4)

                elif vlan[get_interface_name(MAC_table[dest_mac])] == str(vlan_id):
                    # access link => same vlan
                    send_to_link(MAC_table[dest_mac], data, length)
            else:
                # we send data everywhere, because we don't know the right path yet
                for i in interfaces:
                    if i != interface:
                        if vlan[get_interface_name(i)] == "T":
                            # trunk link => add tag
                            if port_state[get_interface_name(i)] == "LISTENING":
                                data_tag = data[0:12] + create_vlan_tag(vlan_id) + data[12:]
                                send_to_link(i, data_tag, length + 4)

                        elif vlan[get_interface_name(i)] == str(vlan_id):
                            # access link => same vlan
                            send_to_link(i, data, length)
        else:
            # broadcast
            for i in interfaces:
                if i != interface:
                    if vlan[get_interface_name(i)] == "T":
                        if port_state[get_interface_name(i)] == "LISTENING":
                            # trunk link => add tag
                            data_tag = data[0:12] + create_vlan_tag(vlan_id) + data[12:]
                            send_to_link(i, data_tag, length + 4)

                    elif vlan[get_interface_name(i)] == str(vlan_id):
                        # access link => same vlan
                        send_to_link(i, data, length)

        # data is of type bytes.
        # send_to_link(i, data, length)

if __name__ == "__main__":
    main()
