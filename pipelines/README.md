# Jenkins Pipelines

This directory contains Jenkins pipeline definitions (Jenkinsfiles) for Mac infrastructure automation.

## Available Pipelines

### Add_Remove_Mac.Jenkinsfile

Orchestrates the process of adding or removing Mac hosts from the infrastructure.

**Workflow:**
1. Update DNS (PowerDNS)
2. Update Nautobot IPAM (optional)
3. Update DHCP Configuration
4. Deploy DHCP Configuration
5. Generate Ansible Host Vars
6. Commit and Push Changes

**Parameters:**
| Parameter | Description |
|-----------|-------------|
| `ACTION` | add or remove |
| `CSV_FILE` | CSV file with hostname,mac,ip data |
| `DOMAIN` | Domain suffix for hostnames |
| `DRY_RUN` | Preview changes without applying |
| `SKIP_*` | Skip individual steps |

**Required Credentials:**
- `powerdns-api-key` - PowerDNS API key
- `github-credentials` - GitHub username/token
- `nautobot-token` - Nautobot API token (optional)

### Mac_Base_Config.Jenkinsfile

Applies base configuration to Mac machines using Ansible.

**Parameters:**
| Parameter | Description |
|-----------|-------------|
| `TARGET` | Ansible host pattern |
| `PLAYBOOK` | Playbook to execute |
| `TAGS` | Ansible tags to run |
| `CHECK_MODE` | Dry run mode |
| `VERBOSE` | Verbose output |

**Required Credentials:**
- `ssh-key-macfarm` - SSH private key
- `github-credentials` - GitHub credentials

### Install_Xcode_CLI.Jenkinsfile

Installs Xcode Command Line Tools on Mac machines.

**Parameters:**
| Parameter | Description |
|-----------|-------------|
| `TARGET` | Ansible host pattern |
| `FORCE_REINSTALL` | Force reinstall |
| `CHECK_MODE` | Dry run mode |

**Required Credentials:**
- `ssh-key-macfarm` - SSH private key
- `github-credentials` - GitHub credentials

## Setup

### 1. Create Jenkins Credentials

Create the following credentials in Jenkins:

```
Credentials > System > Global credentials > Add Credentials
```

| ID | Type | Description |
|----|------|-------------|
| `powerdns-api-key` | Secret text | PowerDNS API key |
| `github-credentials` | Username with password | GitHub username/token |
| `nautobot-token` | Secret text | Nautobot API token |
| `ssh-key-macfarm` | SSH Username with private key | SSH key for Mac access |

### 2. Create Pipeline Jobs

For each pipeline:

1. New Item > Pipeline
2. Configure > Pipeline > Definition: Pipeline script from SCM
3. SCM: Git
4. Repository URL: Your repository
5. Script Path: `pipelines/<Jenkinsfile>`

### 3. Environment Variables

Set these environment variables in Jenkins (Manage Jenkins > Configure System):

| Variable | Description |
|----------|-------------|
| `POWERDNS_URL` | PowerDNS server URL |
| `NAUTOBOT_URL` | Nautobot server URL |

Or configure in each job's environment block.

## Usage Examples

### Adding New Mac Hosts

1. Create CSV file:
   ```csv
   hostname,mac,ip
   build-mac-01,00:11:22:33:44:01,10.0.0.101
   build-mac-02,00:11:22:33:44:02,10.0.0.102
   ```

2. Run `Add_Remove_Mac` pipeline:
   - ACTION: add
   - CSV_FILE: Upload the CSV
   - DOMAIN: macfarm.example.com
   - DRY_RUN: true (to preview)

3. Review output, then re-run with DRY_RUN: false

### Configuring Mac Hosts

1. Run `Mac_Base_Config` pipeline:
   - TARGET: build-mac-* (or specific hostname)
   - PLAYBOOK: mac-mini-base-config.yml
   - CHECK_MODE: true (to preview)

2. Review output, then re-run with CHECK_MODE: false

### Installing Xcode CLI Tools

1. Run `Install_Xcode_CLI` pipeline:
   - TARGET: build_macs (group) or all
   - CHECK_MODE: false

## Best Practices

1. **Always use DRY_RUN first** - Preview changes before applying
2. **Target specific hosts** - Avoid running against `all` in production
3. **Use groups** - Define host groups in Ansible inventory
4. **Monitor builds** - Set up notifications for failed builds
5. **Version control** - All changes are committed to Git for audit trail

## Troubleshooting

### SSH Connection Issues

```bash
# Test connectivity manually
ansible -i ansible/hosts.ini <target> -m ping --private-key=/path/to/key
```

### Ansible Errors

Enable verbose mode (`VERBOSE: true`) to see detailed output.

### PowerDNS/DHCP Issues

Check that:
- API keys are correctly configured
- URLs are accessible from Jenkins
- DNS zones exist in PowerDNS

