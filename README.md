# Ubuntu IP Changer (netplan)

Small Python tool to quickly change static IP configuration on Ubuntu Server using **netplan**.

---

## Quick Install

Download and run directly:

### Using `wget`

```bash
wget https://raw.githubusercontent.com/aboodma/Ip-Changer/main/change_ip.py
chmod +x change_ip.py
sudo ./change_ip.py
```

### Using `curl`

```bash
curl -O https://raw.githubusercontent.com/aboodma/Ip-Changer/main/change_ip.py
chmod +x change_ip.py
sudo ./change_ip.py
```

---

## Features

- Backs up existing `/etc/netplan/*.yaml` into a timestamped folder  
- Writes a new netplan config with:
  - One **static** interface (IP/CIDR, gateway, DNS)
  - Optional **DHCP** interface (for LAN)  
- Interactive mode (just run it with no arguments)  
  - Shows available interfaces (name, state, MAC, IPv4)  
  - Lets you select by **number** instead of typing names  
- Non-interactive CLI options (good for scripts / automation)  
- Uses `routes` instead of deprecated `gateway4` for the default route  
- Optional `netplan apply` at the end (`--apply` flag)

---

## Requirements

- Ubuntu Server (18.04+ with netplan)
- Python 3
- Root privileges (`sudo`)

---

## Usage

### Interactive

Just run:

```bash
sudo ./change_ip.py
```

#### You’ll see a list of current interfaces, for example:

```text
Available interfaces for DHCP (optional):
  1) ens33      state=UP   mac=00:00:00:00:00:00 ip=192.168.x.x/24
  2) ens36      state=DOWN mac=00:00:00:00:00:00 ip=no IPv4
Select DHCP (optional) interface by number (Enter for none):

Available interfaces for STATIC:
  1) ens33      state=UP   mac=00:00:00:00:00:00 ip=192.168.x.x/24
  2) ens36      state=DOWN mac=00:00:00:00:00:00 ip=no IPv4
Select STATIC interface by number:
```

Then you’ll be prompted for:

- Static IP with CIDR (e.g. `xxx.xxx.xxx.xxx/xx`)  
- Gateway IP (e.g. `xxx.xxx.xxx.xxx`)  
- DNS servers (comma separated, e.g. `8.8.8.8,8.8.4.4`)  

#### Example flow for a dual-NIC VM

- DHCP interface: `ensxx` (LAN, `192.168.x.x`)  
- STATIC interface: `ensxx` (public / WAN)  
- IP with CIDR: `xxx.xxx.xxx.xxx/xx`  
- Gateway: `xxx.xxx.xxx.xxx`  
- DNS: `8.8.8.8,8.8.4.4`  

The generated netplan config will look like:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    ens33:
      dhcp4: true
    ens36:
      addresses: [xxx.xxx.xxx.xxx/24]
      routes:
        - to: 0.0.0.0/0
          via: xxx.xxx.xxx.xxx
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

---

### Non-interactive

Provide all required values via CLI:

```bash
sudo ./change_ip.py   --static-interface ens36   --address xxx.xxx.xxx.xxx/24   --gateway xxx.xxx.xxx.xxx   --dns 8.8.8.8 1.1.1.1   --dhcp-interface ens33   --apply
```

- `--static-interface` / `-s` – interface to configure with static IP  
- `--dhcp-interface` – interface to keep with DHCP (optional)  
- `--address` / `-a` – static IP with CIDR  
- `--gateway` / `-g` – gateway IP  
- `--dns` / `-d` – one or more DNS servers (space-separated)  
- `--apply` will run `netplan apply` immediately (⚠️ may disconnect SSH).

---

### Custom netplan directory / output file

By default, the script writes to `/etc/netplan/01-python-netplan.yaml`.  
You can customize the directory and filename:

```bash
sudo ./change_ip.py   -s ens36   -a xxx.xxx.xxx.xxx/24   -g xxx.xxx.xxx.xxx   -d 1.1.1.1   --dhcp-interface ens33   --netplan-dir /etc/netplan   --output 02-custom-static.yaml
```

---

### Notes

- The script creates a backup of all existing netplan YAML files in `/etc/netplan`
  unless you use `--no-backup`.  
- Changing the IP or default route may drop your current SSH session. It’s safer
  to run from local console or via `screen` / `tmux` when changing remote server
  networking.  
- The script uses `routes` with `to: 0.0.0.0/0` for the default route instead of
  the deprecated `gateway4` key.
