# Ansible Directory

This directory contains Ansible playbooks and roles for Mac infrastructure management.

## Structure

```
ansible/
├── hosts.ini                    # Inventory file
├── host_vars/                   # Per-host variables
├── group_vars/                  # Per-group variables
├── mac-mini-base-config.yml     # Base configuration playbook
├── install-xcode-cli-tools.yml  # Xcode CLI tools installation
├── deploy-dhcpd.yml             # DHCP server deployment
└── roles/
    ├── ssh_keys/                # SSH key management
    ├── sudo/                    # Sudo configuration
    ├── homebrew/                # Homebrew installation
    ├── lldpd/                   # LLDP daemon
    ├── telegraf/                # Telegraf monitoring agent
    └── dhcpd/                   # DHCP server configuration
```

## Playbooks

### mac-mini-base-config.yml

Applies base configuration to Mac machines:
- Network configuration (static IP, DNS)
- Hostname configuration
- Timezone and NTP settings
- Power settings (always-on, wake on LAN)
- SSH and remote management
- Homebrew packages
- Optional monitoring (LLDP, Telegraf)

```bash
# Apply to all hosts
ansible-playbook -i hosts.ini mac-mini-base-config.yml

# Apply to specific hosts
ansible-playbook -i hosts.ini mac-mini-base-config.yml --limit "build-mac-*"

# Run specific tags
ansible-playbook -i hosts.ini mac-mini-base-config.yml --tags "network,hostname"

# Dry run
ansible-playbook -i hosts.ini mac-mini-base-config.yml --check
```

### install-xcode-cli-tools.yml

Installs Xcode Command Line Tools on Mac machines.

```bash
ansible-playbook -i hosts.ini install-xcode-cli-tools.yml
```

### deploy-dhcpd.yml

Deploys DHCP server configuration with validation.

```bash
ansible-playbook -i hosts.ini deploy-dhcpd.yml
```

## Roles

### ssh_keys

Manages SSH authorized keys.

Variables:
- `ssh_user`: Target user (default: `buildadmin`)
- `ssh_user_group`: User group (default: `admin`)
- `role_ssh_keys`: List of SSH public keys to authorize

### sudo

Configures sudo access.

Variables:
- `sudo_user`: User to configure (default: `buildadmin`)
- `sudo_nopasswd`: Enable passwordless sudo (default: `true`)

### homebrew

Installs Homebrew and packages.

Variables:
- `homebrew_packages`: List of CLI packages to install
- `homebrew_cask_packages`: List of GUI applications to install
- `homebrew_update`: Update Homebrew before installing (default: `false`)

### lldpd

Installs LLDP daemon for network discovery.

Variables:
- `lldpd_interfaces`: Interfaces to enable LLDP on (default: `en*`)

### telegraf

Installs Telegraf monitoring agent.

Variables:
- `telegraf_influxdb_url`: InfluxDB URL
- `telegraf_influxdb_token`: Authentication token
- `telegraf_prometheus_enabled`: Enable Prometheus metrics endpoint

### dhcpd

Deploys ISC DHCP server configuration.

Variables:
- `dhcpd_config_path`: Configuration file path
- `dhcpd_domain`: Domain for DHCP clients
- `dhcpd_dns_servers`: DNS servers to provide

## Host Variables

The `host_vars/` directory contains per-host configuration. Each file should be named `<hostname>.yml` and can contain:

```yaml
# host_vars/build-mac-01.macfarm.example.com.yml
static_ip: "10.0.0.101"
my_hostname: "build-mac-01.macfarm.example.com"
my_shortname: "build-mac-01"

# Optional overrides
homebrew_packages:
  - git
  - jq
  - node
```

## Group Variables

Create group-specific variables in `group_vars/`:

```yaml
# group_vars/build_macs.yml
install_xcode: true
homebrew_packages:
  - git
  - cocoapods
  - fastlane
```

## Requirements

Install Ansible and required collections:

```bash
pip install ansible
ansible-galaxy collection install community.general
```

## SSH Configuration

Ensure SSH access to target hosts:

```bash
# Test connectivity
ansible -i hosts.ini all -m ping

# Using specific SSH key
ansible -i hosts.ini all -m ping --private-key=~/.ssh/id_rsa_macfarm
```

