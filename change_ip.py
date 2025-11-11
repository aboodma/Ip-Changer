#!/usr/bin/env python3
"""
change_ip.py - Simple netplan-based IP changer for Ubuntu Server.

Features:
- Backs up existing netplan YAML files to a timestamped folder.
- Writes a new netplan config with:
    * one optional DHCP interface (LAN)
    * one static IP interface (WAN)
- Can run interactively or via CLI arguments (non-interactive).
- Optionally applies the config using `netplan apply`.
- Interactive mode lists current interfaces and lets you choose by number.

Usage examples:

Interactive:
    sudo ./change_ip.py

Non-interactive:
    sudo ./change_ip.py \
        --static-interface ens36 \
        --address 212.57.15.138/24 \
        --gateway 212.57.15.129 \
        --dns 8.8.8.8 8.8.4.4 \
        --dhcp-interface ens33 \
        --apply
"""

import argparse
import os
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple

DEFAULT_NETPLAN_DIR = "/etc/netplan"
DEFAULT_OUTPUT_FILE = "01-python-netplan.yaml"


# -------------------- helpers --------------------


def ensure_root() -> None:
    """Ensure the script is running as root."""
    if os.geteuid() != 0:
        raise SystemExit("[-] Please run this script with sudo or as root.")


def run_cmd(cmd: List[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command {' '.join(cmd)} failed: {result.stderr.strip()}")
    return result.stdout


def get_interfaces() -> Dict[str, Dict[str, object]]:
    """
    Return a dict of interfaces with basic info from `ip`:
    {
        "ens33": {"state": "UP", "mac": "00:11:22:33:44:55", "ips": ["192.168.1.10/24"]},
        ...
    }
    """
    interfaces: Dict[str, Dict[str, object]] = {}

    # link info (state, mac)
    link_output = run_cmd(["ip", "-o", "link", "show"])
    for line in link_output.splitlines():
        # format: "2: ens33: <BROADCAST,...> mtu ... link/ether xx:xx:..."
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        name = parts[1].strip()
        rest = parts[2]

        state = "DOWN"
        if "<" in rest and ">" in rest:
            flags = rest.split("<", 1)[1].split(">", 1)[0].split(",")
            if "UP" in flags:
                state = "UP"

        mac = None
        tokens = rest.split()
        for i, t in enumerate(tokens):
            if t == "link/ether" and i + 1 < len(tokens):
                mac = tokens[i + 1]
                break

        interfaces[name] = {"state": state, "mac": mac, "ips": []}

    # address info (IPs)
    addr_output = run_cmd(["ip", "-o", "addr", "show"])
    for line in addr_output.splitlines():
        # e.g.: "2: ens33    inet 192.168.1.67/24 brd ... ..."
        parts = line.split()
        if len(parts) < 4:
            continue
        name = parts[1]
        family = parts[2]
        addr = parts[3]
        if family == "inet":
            if name not in interfaces:
                interfaces[name] = {"state": "UNKNOWN", "mac": None, "ips": []}
            interfaces[name]["ips"].append(addr)

    return interfaces


def choose_interface(
    interfaces: Dict[str, Dict[str, object]],
    purpose: str,
    allow_empty: bool,
) -> Optional[str]:
    """
    Print interfaces and let user choose by number.
    Return interface name or None (if allow_empty and user presses Enter).
    """
    names = sorted(interfaces.keys())
    if not names:
        print("[-] No interfaces found.")
        return None

    print(f"\nAvailable interfaces for {purpose}:")
    for idx, name in enumerate(names, start=1):
        info = interfaces[name]
        ips = info["ips"] or []
        ip_text = ", ".join(ips) if ips else "no IPv4"
        mac = info["mac"] or "-"
        state = info["state"]
        print(f"  {idx}) {name:10} state={state:4} mac={mac:17} ip={ip_text}")

    while True:
        msg = f"Select {purpose} interface by number"
        if allow_empty:
            msg += " (Enter for none)"
        msg += ": "

        choice = input(msg).strip()
        if not choice and allow_empty:
            return None
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(names):
                return names[idx - 1]
        print("Invalid choice, try again.")


def backup_netplan(netplan_dir: str) -> str:
    """Backup existing netplan YAML files to a timestamped folder.

    Returns the backup directory path.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = os.path.join(netplan_dir, f"backup-{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)

    backed_up_any = False
    for fname in os.listdir(netplan_dir):
        if fname.endswith((".yaml", ".yml")):
            src = os.path.join(netplan_dir, fname)
            dst = os.path.join(backup_dir, fname)
            shutil.copy2(src, dst)
            backed_up_any = True

    if backed_up_any:
        print(f"[+] Netplan backup created at: {backup_dir}")
    else:
        print(f"[*] No YAML files found in {netplan_dir}, nothing to backup.")

    return backup_dir


def build_netplan_yaml(
    static_interface: str,
    address: str,
    gateway: str,
    dns_list: List[str],
    dhcp_interface: Optional[str] = None,
) -> str:
    """
    Build the netplan YAML content as a string.

    network:
      version: 2
      renderer: networkd
      ethernets:
        <dhcp_interface>:
          dhcp4: true
        <static_interface>:
          addresses: [IP/CIDR]
          routes:
            - to: 0.0.0.0/0
              via: GATEWAY
          nameservers:
            addresses: [DNS...]
    """
    dns_yaml = ", ".join(dns_list)

    yaml_lines = [
        "network:",
        "  version: 2",
        "  renderer: networkd",
        "  ethernets:",
    ]

    if dhcp_interface:
        yaml_lines += [
            f"    {dhcp_interface}:",
            "      dhcp4: true",
        ]

    yaml_lines += [
        f"    {static_interface}:",
        f"      addresses: [{address}]",
        "      routes:",
        "        - to: 0.0.0.0/0",
        f"          via: {gateway}",
        "      nameservers:",
        f"        addresses: [{dns_yaml}]",
    ]

    return "\n".join(yaml_lines) + "\n"


def write_netplan_file(content: str, netplan_dir: str, output_file: str) -> str:
    """Write the YAML content to the specified netplan file.

    Returns the full path to the written file.
    """
    os.makedirs(netplan_dir, exist_ok=True)
    target_path = os.path.join(netplan_dir, output_file)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    # secure permissions
    os.chmod(target_path, 0o600)
    print(f"[+] Wrote new config to: {target_path}")
    return target_path


def apply_netplan() -> None:
    """Run `netplan apply` to apply the new configuration."""
    print("[+] Applying netplan (this may disconnect your SSH session!)")
    try:
        subprocess.run(["netplan", "apply"], check=True)
        print("[+] netplan apply executed successfully.")
    except FileNotFoundError:
        print("[-] `netplan` command not found. Are you on Ubuntu with netplan?")
    except subprocess.CalledProcessError as e:
        print("[-] Error running netplan apply:", e)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Change Ubuntu static IP using netplan (with optional DHCP interface).",
        epilog="If required arguments are missing, interactive mode will be used."
    )

    parser.add_argument(
        "--static-interface",
        "-s",
        help="Interface to configure with static IP (e.g. ens36, eth1)"
    )
    parser.add_argument(
        "--dhcp-interface",
        help="Interface to keep with DHCP (e.g. ens33). Optional."
    )
    parser.add_argument(
        "--address",
        "-a",
        help="Static IP address with CIDR (e.g. 212.57.15.138/24)"
    )
    parser.add_argument(
        "--gateway",
        "-g",
        help="Gateway IP (e.g. 212.57.15.129)"
    )
    parser.add_argument(
        "--dns",
        "-d",
        nargs="+",
        help="DNS servers (space separated, e.g. 8.8.8.8 8.8.4.4)"
    )
    parser.add_argument(
        "--netplan-dir",
        default=DEFAULT_NETPLAN_DIR,
        help=f"Netplan configuration directory (default: {DEFAULT_NETPLAN_DIR})"
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        help=f"Netplan YAML file name to write (default: {DEFAULT_OUTPUT_FILE})"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply configuration immediately using `netplan apply`"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a backup of existing netplan files"
    )

    return parser.parse_args()


# -------------------- interactive input --------------------


def interactive_input() -> Tuple[Optional[str], str, str, str, List[str]]:
    """Prompt the user interactively.

    Returns: (dhcp_interface, static_interface, address, gateway, dns_list)
    """
    print("=== Ubuntu IP changer (netplan) - Interactive mode ===")

    interfaces = get_interfaces()

    dhcp_if = choose_interface(interfaces, "DHCP (optional)", allow_empty=True)
    static_if = choose_interface(interfaces, "STATIC", allow_empty=False)

    if dhcp_if and static_if and dhcp_if == static_if:
        print("[*] DHCP and static interface are the same, clearing DHCP.")
        dhcp_if = None

    address = input("New static IP with CIDR (e.g. 212.57.15.138/24): ").strip()
    gateway = input("Gateway (e.g. 212.57.15.129): ").strip()
    dns_raw = input("DNS servers (comma separated, e.g. 8.8.8.8,8.8.4.4): ").strip()
    dns_list = [d.strip() for d in dns_raw.split(",") if d.strip()]

    return dhcp_if, static_if, address, gateway, dns_list


# -------------------- main --------------------


def main() -> None:
    ensure_root()
    args = parse_args()

    have_cli_static = args.static_interface and args.address and args.gateway and args.dns

    if not have_cli_static:
        # Interactive mode (with interface selection)
        dhcp_if, static_if, address, gateway, dns_list = interactive_input()
    else:
        dhcp_if = args.dhcp_interface or None
        static_if = args.static_interface
        address = args.address
        gateway = args.gateway
        dns_list = args.dns

    # Basic validation
    if not static_if:
        raise SystemExit("[-] Static interface is required.")
    if not address or "/" not in address:
        raise SystemExit("[-] Address with CIDR is required, e.g. 212.57.15.138/24.")
    if not gateway:
        raise SystemExit("[-] Gateway is required.")
    if not dns_list:
        raise SystemExit("[-] At least one DNS server is required.")

    # Backup (unless disabled)
    if not args.no_backup:
        backup_netplan(args.netplan_dir)
    else:
        print("[*] Skipping backup as requested (--no-backup).")

    # Build and write config
    yaml_content = build_netplan_yaml(
        static_interface=static_if,
        address=address,
        gateway=gateway,
        dns_list=dns_list,
        dhcp_interface=dhcp_if,
    )

    print("\nGenerated netplan config:\n")
    print(yaml_content)

    write_netplan_file(yaml_content, args.netplan_dir, args.output)

    # Apply or ask user
    if args.apply and have_cli_static:
        apply_netplan()
    else:
        confirm = input("\nApply this configuration now? [y/N]: ").strip().lower()
        if confirm == "y":
            apply_netplan()
        else:
            print("[*] Skipped netplan apply. You can apply manually with: sudo netplan apply")


if __name__ == "__main__":
    main()
