#!/usr/bin/env python3
"""
change_ip.py - Simple netplan-based IP changer for Ubuntu Server.

Features:
- Backs up existing netplan YAML files to a timestamped folder.
- Writes a new netplan config with static IP for a single interface.
- Can run interactively or via CLI arguments (non-interactive).
- Optionally applies the config using `netplan apply`.

Usage examples:

Interactive:
    sudo ./change_ip.py

Non-interactive:
    sudo ./change_ip.py \
        --interface ens33 \
        --address 192.168.1.50/24 \
        --gateway 192.168.1.1 \
        --dns 8.8.8.8 1.1.1.1 \
        --apply
"""

import argparse
import os
import shutil
import subprocess
from datetime import datetime
from typing import List

DEFAULT_NETPLAN_DIR = "/etc/netplan"
DEFAULT_OUTPUT_FILE = "01-python-netplan.yaml"


def ensure_root() -> None:
    """Ensure the script is running as root."""
    if os.geteuid() != 0:
        raise SystemExit("[-] Please run this script with sudo or as root.")


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


def build_netplan_yaml(interface: str, address: str, gateway: str, dns_list: List[str]) -> str:
    """Build the netplan YAML content as a string."""
    dns_yaml = ", ".join(dns_list)
    yaml_content = f"""network:
  version: 2
  renderer: networkd
  ethernets:
    {interface}:
      addresses: [{address}]
      gateway4: {gateway}
      nameservers:
        addresses: [{dns_yaml}]
"""
    return yaml_content


def write_netplan_file(content: str, netplan_dir: str, output_file: str) -> str:
    """Write the YAML content to the specified netplan file.

    Returns the full path to the written file.
    """
    os.makedirs(netplan_dir, exist_ok=True)
    target_path = os.path.join(netplan_dir, output_file)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
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
        description="Change Ubuntu static IP using netplan.",
        epilog="If no arguments are given, interactive mode will be used."
    )

    parser.add_argument(
        "-i", "--interface",
        help="Network interface name (e.g. ens33, eth0)"
    )
    parser.add_argument(
        "-a", "--address",
        help="IP address with CIDR (e.g. 192.168.1.50/24)"
    )
    parser.add_argument(
        "-g", "--gateway",
        help="Gateway IP (e.g. 192.168.1.1)"
    )
    parser.add_argument(
        "-d", "--dns",
        nargs="+",
        help="DNS servers (space separated, e.g. 8.8.8.8 1.1.1.1)"
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


def interactive_input() -> tuple[str, str, str, List[str]]:
    """Prompt the user for interface/address/gateway/dns values interactively."""
    print("=== Ubuntu IP changer (netplan) - Interactive mode ===")
    interface = input("Interface name (e.g. ens33, eth0): ").strip()
    address = input("New IP with CIDR (e.g. 192.168.1.50/24): ").strip()
    gateway = input("Gateway (e.g. 192.168.1.1): ").strip()
    dns_raw = input("DNS servers (comma separated, e.g. 8.8.8.8,1.1.1.1): ").strip()
    dns_list = [d.strip() for d in dns_raw.split(",") if d.strip()]
    return interface, address, gateway, dns_list


def main() -> None:
    ensure_root()
    args = parse_args()

    # Decide if we are in interactive or non-interactive mode
    interactive = not (args.interface and args.address and args.gateway and args.dns)

    if interactive:
        interface, address, gateway, dns_list = interactive_input()
    else:
        interface = args.interface
        address = args.address
        gateway = args.gateway
        dns_list = args.dns

    # Basic validation
    if not interface or not address or not gateway or not dns_list:
        raise SystemExit("[-] Interface, address, gateway, and at least one DNS server are required.")

    # Backup (unless disabled)
    if not args.no_backup:
        backup_netplan(args.netplan_dir)
    else:
        print("[*] Skipping backup as requested (--no-backup).")

    # Build and write config
    yaml_content = build_netplan_yaml(interface, address, gateway, dns_list)
    print("\nGenerated netplan config:\n")
    print(yaml_content)

    write_netplan_file(yaml_content, args.netplan_dir, args.output)

    # Apply or ask user
    if args.apply:
        apply_netplan()
    else:
        if interactive:
            confirm = input("\nApply this configuration now? [y/N]: ").strip().lower()
            if confirm == "y":
                apply_netplan()
            else:
                print("[*] Skipped netplan apply. You can apply manually with: sudo netplan apply")
        else:
            print("\n[*] Not applying automatically (no --apply).")
            print("    To apply the configuration manually, run: sudo netplan apply")


if __name__ == "__main__":
    main()
