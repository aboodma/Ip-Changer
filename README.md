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

### Using `Curl`

```bash
curl -O https://raw.githubusercontent.com/aboodma/Ip-Changer/main/change_ip.py
chmod +x change_ip.py
sudo ./change_ip.py
```
---

## Features
- Backs up existing /etc/netplan/*.yaml into a timestamped folder

- Writes a new static IP config for a single interface

- Interactive mode (just run it with no arguments)

- Non-interactive CLI options (good for scripts / automation)

- Optional netplan apply at the end (--apply flag)

## Requirements
- Ubuntu Server (18.04+ with netplan)

- Python 3

- Root privileges (`sudo`)

## Usage

### Interactive

Just run:

```bash
sudo ./change_ip.py
```

You’ll be prompted for:

- Interface name (e.g. ens33, eth0)

- IP with CIDR (e.g. 192.168.1.50/24)

- Gateway (e.g. 192.168.1.1)

- DNS servers (comma separated)
---
### Non-interactive

Provide all required values via CLI:
```bash
sudo ./change_ip.py \
  --interface ens33 \
  --address 192.168.1.50/24 \
  --gateway 192.168.1.1 \
  --dns 8.8.8.8 1.1.1.1 \
  --apply
```
- --dns accepts one or more DNS servers (space-separated).

- --apply will run netplan apply immediately (⚠️ may disconnect SSH).

---
### Custom netplan directory / output file
By default, the script writes to `/etc/netplan/01-python-netplan.yaml`.
You can customize the directory and filename:

```bash
sudo ./change_ip.py \
  -i ens33 \
  -a 10.10.0.10/24 \
  -g 10.10.0.1 \
  -d 1.1.1.1 \
  --netplan-dir /etc/netplan \
  --output 02-custom-static.yaml
```

---
### Notes
- The script creates a backup of all existing netplan YAML files in /etc/netplan unless you use --no-backup.

- Changing the IP may drop your current SSH session. It’s safer to run from local console or via screen/tmux.




