# Ansible Directory

This directory contains Ansible playbooks and roles for Mac infrastructure management.

## Structure

```
ansible/
├── hosts.ini                       # Inventory file
├── host_vars/                      # Per-host variables
├── group_vars/                     # Per-group variables
├── mac-mini-base-config.yml        # Base configuration playbook
├── install-xcode-cli-tools.yml     # Xcode CLI tools installation
├── deploy-dhcpd.yml                # DHCP server deployment
├── mac-cleanup.yml                 # Cleanup/reset Mac machines
├── reboot.yml                      # Reboot Mac machines
├── install-rosetta.yml             # Install Rosetta 2 (Apple Silicon)
├── disable-bluetooth.yml           # Disable Bluetooth
├── disable-wifi.yml                # Disable Wi-Fi
├── fix-ard.yml                     # Fix Apple Remote Desktop
├── fix-dns.yml                     # Configure DNS servers
├── fix-timezone.yml                # Configure timezone
├── remote-desktop.yml              # Enable Remote Desktop/ARD
├── software-update.yml             # Run macOS software updates
├── query-lldp.yml                  # Query LLDP network info
├── jamf-recon.yml                  # Run Jamf inventory commands
├── renew-enrollment.yml            # Renew MDM enrollment
├── promote-user-to-admin.yml       # Promote user to admin
├── demote-user-from-admin.yml      # Demote user from admin
├── remove-local-user.yml           # Remove local user account
├── secure-token.yml                # Manage FileVault Secure Token
├── configure-zsh.yml               # Configure ZSH shell
├── install-lldpd.yml               # Install LLDP daemon
├── install-telegraf.yml            # Install Telegraf monitoring
├── configure-sudo.yml              # Configure sudo access
├── deploy-ssh-keys.yml             # Deploy SSH keys
├── install-minimum-brew.yml        # Install essential Homebrew packages
├── configure-shell-env.yml         # Configure shell environment
├── clear-nvram.yml                 # Clear NVRAM and reboot
├── reset-hostname.yml              # Reset hostname to generic name
├── fix-xcode-after-upgrade.yml     # Fix Xcode after upgrade
├── configure-auto-login.yml        # Configure auto-login
└── roles/
    ├── ssh_keys/                   # SSH key management
    ├── sudo/                       # Sudo configuration
    ├── homebrew/                   # Homebrew installation
    ├── lldpd/                      # LLDP daemon
    ├── telegraf/                   # Telegraf monitoring agent
    └── dhcpd/                      # DHCP server configuration
```

## Playbooks Reference

### Core Configuration

#### mac-mini-base-config.yml

Applies base configuration to Mac machines:
- Network configuration (static IP, DNS)
- Hostname configuration
- Timezone and NTP settings
- Power settings (always-on, wake on LAN)
- SSH and remote management
- Homebrew packages
- Optional monitoring (LLDP, Telegraf)

```bash
ansible-playbook -i hosts.ini mac-mini-base-config.yml
ansible-playbook -i hosts.ini mac-mini-base-config.yml --limit "build-mac-*"
ansible-playbook -i hosts.ini mac-mini-base-config.yml --tags "network,hostname"
```

#### install-xcode-cli-tools.yml

Installs Xcode Command Line Tools on Mac machines.

```bash
ansible-playbook -i hosts.ini install-xcode-cli-tools.yml
```

#### install-rosetta.yml

Installs Rosetta 2 on Apple Silicon Macs for x86_64 compatibility.

```bash
ansible-playbook -i hosts.ini install-rosetta.yml -e "target_hosts=apple_silicon_macs"
```

#### fix-xcode-after-upgrade.yml

Fixes Xcode configuration after macOS or Xcode upgrades (accepts license, installs packages, enables developer mode).

```bash
ansible-playbook -i hosts.ini fix-xcode-after-upgrade.yml
```

### Network & System

#### fix-dns.yml

Configures DNS servers on Mac machines.

```bash
ansible-playbook -i hosts.ini fix-dns.yml -e "dns_server_list=['8.8.8.8','8.8.4.4']"
```

#### fix-timezone.yml

Configures timezone on Mac machines.

```bash
ansible-playbook -i hosts.ini fix-timezone.yml -e "timezone='America/New_York'"
```

#### deploy-dhcpd.yml

Deploys DHCP server configuration with validation.

```bash
ansible-playbook -i hosts.ini deploy-dhcpd.yml
```

#### query-lldp.yml

Queries LLDP information from Mac machines to identify network switch ports.

```bash
ansible-playbook -i hosts.ini query-lldp.yml
# Results saved to ./lldp_results/
```

### Security & Hardening

#### disable-bluetooth.yml

Disables Bluetooth on Mac machines (useful for build farm security).

```bash
ansible-playbook -i hosts.ini disable-bluetooth.yml
```

#### disable-wifi.yml

Disables Wi-Fi on Mac machines.

```bash
ansible-playbook -i hosts.ini disable-wifi.yml
```

#### secure-token.yml

Manages Secure Token for FileVault on Mac machines.

```bash
ansible-playbook -i hosts.ini secure-token.yml -e "token_user=buildadmin"
```

### Remote Access

#### remote-desktop.yml

Enables Apple Remote Desktop (ARD) / Screen Sharing for remote management.

```bash
ansible-playbook -i hosts.ini remote-desktop.yml
```

#### fix-ard.yml

Resets broken Screen Sharing / Remote Management on macOS.

```bash
ansible-playbook -i hosts.ini fix-ard.yml
```

### User Management

#### promote-user-to-admin.yml

Promotes a user to admin group on Mac machines.

```bash
ansible-playbook -i hosts.ini promote-user-to-admin.yml -e "promote_user=buildagent"
```

#### demote-user-from-admin.yml

Removes a user from the admin group.

```bash
ansible-playbook -i hosts.ini demote-user-from-admin.yml -e "demote_user=tempuser"
```

#### remove-local-user.yml

Removes a local user account and home directory.

```bash
ansible-playbook -i hosts.ini remove-local-user.yml -e "remove_user=olduser"
ansible-playbook -i hosts.ini remove-local-user.yml -e "remove_user=olduser secure_removal=true"
```

#### configure-auto-login.yml

Configures automatic login for a user (use only in controlled environments).

```bash
ansible-playbook -i hosts.ini configure-auto-login.yml -e "login_user=buildagent"
```

### Software & Packages

#### software-update.yml

Manages macOS software updates.

```bash
# List available updates
ansible-playbook -i hosts.ini software-update.yml

# Install specific update
ansible-playbook -i hosts.ini software-update.yml -e "update_name='macOS Sonoma 14.7.2-23H311'"
```

#### install-minimum-brew.yml

Installs minimum required Homebrew packages for build machines.

```bash
ansible-playbook -i hosts.ini install-minimum-brew.yml
```

#### install-lldpd.yml

Installs and configures LLDPD for network discovery.

```bash
ansible-playbook -i hosts.ini install-lldpd.yml
```

#### install-telegraf.yml

Installs Telegraf monitoring agent using the telegraf role.

```bash
ansible-playbook -i hosts.ini install-telegraf.yml
```

### Shell & Environment

#### configure-zsh.yml

Configures ZSH as the default shell and migrates bash profiles.

```bash
ansible-playbook -i hosts.ini configure-zsh.yml -e "zsh_user=buildadmin"
```

#### configure-shell-env.yml

Configures shell environment (PATH for Homebrew, etc.).

```bash
ansible-playbook -i hosts.ini configure-shell-env.yml
```

#### configure-sudo.yml

Configures sudo access using the sudo role.

```bash
ansible-playbook -i hosts.ini configure-sudo.yml
```

#### deploy-ssh-keys.yml

Deploys SSH keys using the ssh_keys role.

```bash
ansible-playbook -i hosts.ini deploy-ssh-keys.yml
```

### Jamf/MDM

#### jamf-recon.yml

Runs Jamf management commands to update inventory and apply policies.

```bash
ansible-playbook -i hosts.ini jamf-recon.yml
ansible-playbook -i hosts.ini jamf-recon.yml -e "jamf_run_policy=true"
```

#### renew-enrollment.yml

Renews MDM enrollment profile on Mac machines.

```bash
ansible-playbook -i hosts.ini renew-enrollment.yml
```

### Maintenance & Reset

#### mac-cleanup.yml

Cleans up and resets Mac machines to a baseline state.

```bash
ansible-playbook -i hosts.ini mac-cleanup.yml -e "target_hosts=decommission_targets"
```

#### reboot.yml

Simple playbook to reboot Mac machines.

```bash
ansible-playbook -i hosts.ini reboot.yml
```

#### clear-nvram.yml

Clears NVRAM and reboots Mac machines.

```bash
ansible-playbook -i hosts.ini clear-nvram.yml
```

#### reset-hostname.yml

Resets Mac hostname to a generic/randomized name.

```bash
ansible-playbook -i hosts.ini reset-hostname.yml -e "new_hostname_prefix='available-mac'"
```

## Roles

### ssh_keys

Manages SSH authorized keys.

Variables:
- `ssh_user`: Target user (default: `automation_user`)
- `ssh_user_group`: User group (default: `admin`)
- `role_ssh_keys`: List of SSH public keys to authorize

### sudo

Configures sudo access.

Variables:
- `sudo_user`: User to configure (default: `automation_user`)
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

## Common Variables

Most playbooks support these common variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `target_hosts` | Ansible host pattern | varies |
| `admin_user` | SSH and admin user | `automation_user` |

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

## Usage Examples

### Provision a New Mac

```bash
# 1. Base configuration
ansible-playbook -i hosts.ini mac-mini-base-config.yml --limit "new-mac-01"

# 2. Install Xcode CLI tools
ansible-playbook -i hosts.ini install-xcode-cli-tools.yml --limit "new-mac-01"

# 3. Install Rosetta (if Apple Silicon)
ansible-playbook -i hosts.ini install-rosetta.yml --limit "new-mac-01"

# 4. Deploy SSH keys
ansible-playbook -i hosts.ini deploy-ssh-keys.yml --limit "new-mac-01"
```

### Decommission a Mac

```bash
# 1. Run cleanup
ansible-playbook -i hosts.ini mac-cleanup.yml --limit "old-mac-01"

# 2. Reset hostname
ansible-playbook -i hosts.ini reset-hostname.yml --limit "old-mac-01"

# 3. Clear NVRAM
ansible-playbook -i hosts.ini clear-nvram.yml --limit "old-mac-01"
```

### Security Hardening

```bash
# Disable wireless interfaces
ansible-playbook -i hosts.ini disable-wifi.yml
ansible-playbook -i hosts.ini disable-bluetooth.yml

# Configure sudo and SSH
ansible-playbook -i hosts.ini configure-sudo.yml
ansible-playbook -i hosts.ini deploy-ssh-keys.yml
```
