# Scripts Directory

This directory contains utility scripts for Mac infrastructure management.

## Quick Start

**Collect inventory from existing Macs and provision them:**

```bash
# Step 1: Collect MAC addresses and hostnames from existing machines
./mac_inventory_collector.py --ip 10.0.0.100-120 --output /tmp/new_macs.csv

# Step 2: Provision using collected data
./mac_provisioning_manager.py --file /tmp/new_macs.csv --domain macfarm.example.com
```

**Provision a new Mac in one command:**

```bash
./mac_provisioning_manager.py \
  --hostname build-mac-01.macfarm.example.com \
  --mac 00:11:22:33:44:55 \
  --ip 10.0.0.100 \
  --domain macfarm.example.com
```

## Workflow

### Data Collection (Optional - for existing machines)
```
Mac Inventory Collector
    ↓
    └─→ Generates CSV file (hostname, MAC, IP)
```

### Provisioning Workflow
```
Mac Provisioning Manager (Master Script)
    ↓
    ├─→ [1] Nautobot Manager         → Adds IP addresses to Nautobot IPAM
    ↓
    ├─→ [2] PowerDNS Manager         → Creates DNS A records
    ↓
    ├─→ [3] DHCP Reservation Manager → Configures DHCP reservations
    ↓
    ├─→ [4] Ansible Playbook         → Deploys DHCP configuration
    ↓
    └─→ [5] Host Vars Generator      → Creates Ansible host_vars files
```

## Scripts

### mac_provisioning_manager.py

Master orchestration script that executes the complete provisioning workflow.

**Usage:**

```bash
# Single Mac
./mac_provisioning_manager.py \
  --hostname build-mac-01.macfarm.example.com \
  --mac 00:11:22:33:44:55 \
  --ip 10.0.0.100 \
  --domain macfarm.example.com

# Batch from CSV
./mac_provisioning_manager.py \
  --file hosts.csv \
  --domain macfarm.example.com

# Skip specific steps
./mac_provisioning_manager.py \
  --file hosts.csv \
  --domain macfarm.example.com \
  --skip-deploy
```

### powerdns_manager.py

Manages A records in PowerDNS via the REST API.

**Usage:**

```bash
# Add a record
./powerdns_manager.py \
  --domain example.com \
  --hostname server01 \
  --ip 192.168.1.100 \
  --action add

# Remove a record
./powerdns_manager.py \
  --domain example.com \
  --hostname server01 \
  --action remove

# Batch operations
./powerdns_manager.py \
  --domain example.com \
  --file hosts.csv \
  --action add
```

**Environment Variables:**
- `POWERDNS_API_KEY` - PowerDNS API key (required)
- `POWERDNS_SERVER_URL` - PowerDNS server URL (default: http://localhost:8084)

### dhcp_reservation_manager.py

Manages DHCP reservations in dhcpd.conf file.

**Usage:**

```bash
# Add reservation
./dhcp_reservation_manager.py \
  --hostname server01 \
  --mac 00:11:22:33:44:55 \
  --ip 192.168.1.100 \
  --action add

# Remove reservation
./dhcp_reservation_manager.py \
  --hostname server01 \
  --action remove

# Export all reservations
./dhcp_reservation_manager.py \
  --action export \
  --output dhcp_backup.csv
```

### host_vars_generator.py

Generates Ansible host_vars files.

**Usage:**

```bash
# Single host
./host_vars_generator.py \
  --hostname build-mac-01.macfarm.example.com \
  --ip 10.0.0.100

# Batch from CSV
./host_vars_generator.py --file hosts.csv
```

### mac_inventory_collector.py

Collects inventory from existing Mac machines via SSH.

**Usage:**

```bash
# Single IP
./mac_inventory_collector.py --ip 10.0.0.100

# IP range
./mac_inventory_collector.py --ip 10.0.0.100-120

# CIDR
./mac_inventory_collector.py --ip 10.0.0.0/28
```

### nautobot_manager.py

Manages IP addresses in Nautobot IPAM.

**Usage:**

```bash
# Add IP
./nautobot_manager.py \
  --hostname server01 \
  --ip 192.168.1.100 \
  --action add

# Remove IP
./nautobot_manager.py \
  --hostname server01 \
  --ip 192.168.1.100 \
  --action remove
```

**Environment Variables:**
- `NAUTOBOT_URL` - Nautobot server URL
- `NAUTOBOT_TOKEN` - Nautobot API token

## CSV File Format

All scripts use a unified CSV format:

```csv
hostname,mac,ip
build-mac-01.macfarm.example.com,00:11:22:33:44:55,10.0.0.100
build-mac-02.macfarm.example.com,00:11:22:33:44:56,10.0.0.101
```

Headers are optional and will be automatically detected.

## Requirements

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Exit Codes

- `0` - Success
- `1` - Failure (invalid parameters, API errors, etc.)
- `130` - Interrupted by user (Ctrl+C)

