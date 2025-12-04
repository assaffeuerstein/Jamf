# 🍎 Mac Fleet Automation Toolkit

A comprehensive automation toolkit for managing Mac Mini build farm infrastructure at scale. This project provides end-to-end automation for provisioning, configuration management, and lifecycle operations of macOS build machines.

![macOS](https://img.shields.io/badge/macOS-Sequoia%20%7C%20Sonoma-blue)
![Python](https://img.shields.io/badge/Python-3.9+-green)
![Ansible](https://img.shields.io/badge/Ansible-2.14+-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🎯 Overview

This toolkit solves the challenge of managing large-scale Mac Mini build farms by automating:

- **Provisioning**: DNS, DHCP, and IPAM configuration
- **Configuration Management**: Ansible-based system configuration
- **CI/CD Integration**: Jenkins pipelines for operations
- **Web Interface**: Self-service portal for infrastructure teams

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Web Interface (Flask)                       │
│                  Azure AD SSO Authentication                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                    Jenkins Pipelines                             │
│         (MacMiniBaseConfig, AddRemoveMac, SshKeys)              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│               Orchestration Scripts (Python)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ PowerDNS │  │   DHCP   │  │ Nautobot │  │ HostVars │        │
│  │ Manager  │  │ Manager  │  │  IPAM    │  │Generator │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                  Ansible Configuration                           │
│    Roles: homebrew, telegraf, lldpd, ssh_keys, sudo, etc.       │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Features

### Provisioning Automation

- **PowerDNS Integration**: Automated A record management via REST API
- **DHCP Management**: ISC dhcpd reservation configuration with syntax validation
- **IPAM Integration**: Nautobot IP address management
- **Host Variables**: Auto-generated Ansible host_vars files

### Configuration Management

- **Base Configuration**: Network settings, hostname, timezone, power management
- **Homebrew Packages**: Automated installation of required tools
- **Monitoring**: Telegraf agent deployment for metrics collection
- **Network Discovery**: LLDP daemon for network topology mapping
- **Security**: SSH key distribution and sudo configuration

### CI/CD Pipelines

- **MacMiniBaseConfig**: Full system configuration pipeline
- **AddRemoveMac**: Provision/deprovision Mac infrastructure
- **SshKeys**: Bulk SSH key distribution
- **XcodeCommandLineTools**: Bootstrap new machines

### Web Interface

- **Azure AD SSO**: Enterprise authentication
- **Self-Service Portal**: Upload CSV, trigger jobs
- **Apple-Style Design**: Modern, responsive UI

## 📁 Project Structure

```
.
├── ansible/                      # Ansible playbooks and roles
│   ├── roles/
│   │   ├── corretto/            # Amazon Corretto JDK
│   │   ├── dhcpd/               # DHCP server configuration
│   │   ├── homebrew/            # Homebrew package manager
│   │   ├── iterm/               # iTerm2 configuration
│   │   ├── lldpd/               # LLDP daemon
│   │   ├── ssh_keys/            # SSH key distribution
│   │   ├── sudo/                # Sudoers configuration
│   │   └── telegraf/            # Telegraf monitoring agent
│   ├── host_vars/               # Per-host variables
│   ├── mac-mini-base-config.yml # Main configuration playbook
│   └── *.ini                    # Inventory files
│
├── scripts/                      # Python automation scripts
│   ├── mac_provisioning_manager.py  # Master orchestrator
│   ├── powerdns_manager.py          # DNS management
│   ├── dhcp_reservation_manager.py  # DHCP reservations
│   ├── nautobot_manager.py          # IPAM management
│   ├── host_vars_generator.py       # Ansible vars generation
│   ├── mac_inventory_collector.py   # Inventory discovery
│   └── csv_utils.py                 # Shared CSV utilities
│
├── pipelines/                    # Jenkins pipeline definitions
│   ├── Add_Remove_Mac.Jenkinsfile
│   ├── MacMiniBaseConfig.Jenkinsfile
│   ├── SshKeys.Jenkinsfile
│   └── XcodeCommandLineTools.Jenkinsfile
│
├── web/                          # Flask web application
│   ├── app.py                   # Main application
│   ├── config.py                # Configuration
│   ├── templates/               # Jinja2 templates
│   └── static/                  # CSS, JavaScript
│
└── examples/                     # Example files
    ├── macs.csv                 # Example CSV format
    └── inventory.ini            # Example inventory
```

## 🛠️ Quick Start

### Prerequisites

- Python 3.9+
- Ansible 2.14+
- Access to PowerDNS server (for DNS management)
- Access to DHCP server (for reservations)
- Jenkins (for CI/CD pipelines)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mac-fleet-automation.git
cd mac-fleet-automation

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r scripts/requirements.txt

# Verify Ansible installation
ansible --version
```

### Configuration

1. **Set environment variables:**

```bash
# PowerDNS
export POWERDNS_API_KEY="your-api-key"
export POWERDNS_SERVER_URL="http://pdns.example.com:8084"

# Nautobot (optional)
export NAUTOBOT_URL="https://nautobot.example.com"
export NAUTOBOT_TOKEN="your-nautobot-token"
```

2. **Configure Ansible inventory:**

```bash
cp examples/inventory.ini ansible/hosts.ini
# Edit ansible/hosts.ini with your hosts
```

### Usage Examples

#### Provision a Single Mac

```bash
./scripts/mac_provisioning_manager.py \
  --hostname build-mac-01.macfarm.example.com \
  --mac 00:11:22:33:44:55 \
  --ip 10.0.0.100 \
  --domain macfarm.example.com
```

#### Batch Provision from CSV

```bash
./scripts/mac_provisioning_manager.py \
  --file hosts.csv \
  --domain macfarm.example.com
```

#### Collect Inventory from Existing Macs

```bash
./scripts/mac_inventory_collector.py \
  --ip 10.0.0.100-120 \
  --output collected_inventory.csv
```

#### Run Base Configuration

```bash
cd ansible
ansible-playbook -i hosts.ini mac-mini-base-config.yml
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [scripts/README.md](scripts/README.md) | Detailed script documentation |
| [web/README.md](web/README.md) | Web interface setup guide |
| [pipelines/README.md](pipelines/README.md) | Jenkins pipeline documentation |
| [ansible/roles/*/README.md](ansible/roles/) | Individual role documentation |

## 🔧 Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POWERDNS_API_KEY` | PowerDNS API key | Required |
| `POWERDNS_SERVER_URL` | PowerDNS server URL | `http://localhost:8084` |
| `NAUTOBOT_URL` | Nautobot server URL | Optional |
| `NAUTOBOT_TOKEN` | Nautobot API token | Optional |
| `DHCPD_CONF_PATH` | Path to dhcpd.conf | Auto-detected |
| `DHCPD_DOMAIN` | Default DHCP domain | `macfarm.example.com` |

### CSV File Format

```csv
hostname,mac,ip
build-mac-01.macfarm.example.com,00:11:22:33:44:55,10.0.0.100
build-mac-02.macfarm.example.com,00:11:22:33:44:56,10.0.0.101
```

## 🧪 Testing

```bash
# Run Python tests
pytest scripts/tests/

# Validate Ansible syntax
ansible-playbook --syntax-check ansible/mac-mini-base-config.yml

# Lint Ansible playbooks
ansible-lint ansible/

# Lint shell scripts
shellcheck pipelines/*.sh
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by real-world Mac Mini build farm management challenges
- Built with best practices from DevOps and infrastructure automation

## 📧 Contact

- **Author**: Assaf Feuerstein
- **Email**: your.email@example.com
- **LinkedIn**: [Your Profile](https://linkedin.com/in/yourprofile)

---

*Built with ❤️ for macOS infrastructure automation*

