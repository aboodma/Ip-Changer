# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.2.0] - 2025-11-11

### Added
- Interactive interface selection using `ip` output:
  - Lists interfaces with name, state, MAC, and IPv4 address.
  - Allows choosing DHCP and static interfaces by number.
- Support for dual-NIC setups:
  - Optional DHCP interface (e.g. LAN).
  - Static interface with IP/CIDR, gateway, and DNS (e.g. WAN).

### Changed
- Netplan config now uses `routes` with `to: 0.0.0.0/0` instead of deprecated `gateway4`.
- Netplan file is written with secure permissions (`chmod 600`).

## [0.1.0] - 2025-11-11

### Added
- Initial release of `change_ip.py`.
- Backup of existing `/etc/netplan/*.yaml` into timestamped directory.
- Interactive mode for configuring a single static interface.
- Non-interactive CLI flags for automation.
- Optional `--apply` flag to run `netplan apply` automatically.
