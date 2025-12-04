#!/usr/bin/env python3
"""
Mac Provisioning Manager - Master Script

This script orchestrates the complete provisioning workflow for Mac infrastructure:
1. Adds IP addresses to Nautobot IPAM (optional)
2. Creates DNS A records (PowerDNS)
3. Configures DHCP reservations
4. Deploys DHCP configuration via Ansible
5. Generates Ansible host_vars files

Supports both single-host and batch processing modes.
"""

import argparse
import csv
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Import shared CSV parsing utility
from csv_utils import parse_mac_ip_csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class MacProvisioningManager:
    """Orchestrates Mac provisioning workflow across multiple tools."""
    
    def __init__(self, scripts_dir: str, ansible_dir: str):
        """
        Initialize the provisioning manager.
        
        Args:
            scripts_dir: Path to scripts directory
            ansible_dir: Path to ansible directory
        """
        self.scripts_dir = Path(scripts_dir)
        self.ansible_dir = Path(ansible_dir)
        
        # Define script paths
        self.nautobot_script = self.scripts_dir / 'nautobot_manager.py'
        self.powerdns_script = self.scripts_dir / 'powerdns_manager.py'
        self.dhcp_script = self.scripts_dir / 'dhcp_reservation_manager.py'
        self.hostvars_script = self.scripts_dir / 'host_vars_generator.py'
        self.dhcp_playbook = self.ansible_dir / 'dhcpd_deploy.yml'
        
        # Verify required files exist
        self._verify_dependencies()
    
    def _verify_dependencies(self) -> None:
        """Verify that all required scripts and playbooks exist."""
        required_files = [
            self.nautobot_script,
            self.powerdns_script,
            self.dhcp_script,
            self.hostvars_script,
            self.dhcp_playbook
        ]
        
        missing_files = [f for f in required_files if not f.exists()]
        
        if missing_files:
            logger.error("Missing required files:")
            for f in missing_files:
                logger.error(f"  - {f}")
            raise FileNotFoundError("Required dependencies not found")
        
        logger.debug("All dependencies verified")
    
    def _run_command(self, command: List[str], description: str, interactive: bool = False) -> bool:
        """
        Run a shell command and log the results.
        
        Args:
            command: Command to execute as list of arguments
            description: Human-readable description for logging
            interactive: If True, allow user interaction
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Running: {description}")
        logger.debug(f"Command: {' '.join(command)}")
        
        try:
            if interactive:
                result = subprocess.run(command, check=False)
                
                if result.returncode == 0:
                    logger.info(f"✓ {description} completed successfully")
                    return True
                else:
                    logger.error(f"✗ {description} failed with exit code {result.returncode}")
                    return False
            else:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    logger.info(f"✓ {description} completed successfully")
                    if result.stdout:
                        logger.debug(f"Output: {result.stdout}")
                    return True
                else:
                    logger.error(f"✗ {description} failed with exit code {result.returncode}")
                    if result.stdout:
                        logger.error(f"Output: {result.stdout}")
                    if result.stderr:
                        logger.error(f"Error: {result.stderr}")
                    return False
                
        except Exception as e:
            logger.error(f"✗ {description} failed with exception: {e}")
            return False
    
    def provision_nautobot(self, csv_file: Optional[str], hostname: Optional[str],
                          ip: Optional[str], action: str, nautobot_url: Optional[str],
                          nautobot_token: Optional[str], verify_ssl: bool) -> bool:
        """Manage IP addresses in Nautobot."""
        command = [
            'python3',
            str(self.nautobot_script),
            '--action', action
        ]
        
        if nautobot_url:
            command.extend(['--url', nautobot_url])
        
        if nautobot_token:
            command.extend(['--token', nautobot_token])
        
        if not verify_ssl:
            command.append('--no-verify-ssl')
        
        if csv_file:
            command.extend(['--file', csv_file])
        else:
            command.extend(['--hostname', hostname, '--ip', ip])
        
        description = f"Nautobot IP {action}"
        return self._run_command(command, description, interactive=False)
    
    def provision_dns(self, csv_file: Optional[str], hostname: Optional[str], 
                     ip: Optional[str], domain: str, non_interactive: bool) -> bool:
        """Create DNS A records."""
        command = [
            'python3',
            str(self.powerdns_script),
            '--domain', domain,
            '--action', 'add'
        ]
        
        if non_interactive:
            command.append('--non-interactive')
        
        if csv_file:
            command.extend(['--file', csv_file])
        else:
            command.extend(['--hostname', hostname, '--ip', ip])
        
        return self._run_command(command, "DNS record creation", interactive=not non_interactive)
    
    def provision_dhcp(self, csv_file: Optional[str], hostname: Optional[str],
                      mac: Optional[str], ip: Optional[str], non_interactive: bool) -> bool:
        """Create DHCP reservations."""
        command = [
            'python3',
            str(self.dhcp_script),
            '--action', 'add'
        ]
        
        if non_interactive:
            command.append('--non-interactive')
        
        if csv_file:
            command.extend(['--file', csv_file])
        else:
            command.extend(['--hostname', hostname, '--mac', mac, '--ip', ip])
        
        return self._run_command(command, "DHCP reservation creation", interactive=not non_interactive)
    
    def deploy_dhcp(self, inventory_file: Optional[str] = None) -> bool:
        """Deploy DHCP configuration via Ansible."""
        if not inventory_file:
            inventory_file = str(self.ansible_dir / 'hosts.example.ini')
        
        command = [
            'ansible-playbook',
            str(self.dhcp_playbook),
            '-i', inventory_file
        ]
        
        return self._run_command(command, "DHCP deployment (Ansible)")
    
    def generate_host_vars(self, csv_file: Optional[str], hostname: Optional[str],
                          ip: Optional[str], non_interactive: bool = False) -> bool:
        """Generate Ansible host_vars files."""
        command = [
            'python3',
            str(self.hostvars_script)
        ]
        
        if non_interactive:
            command.append('--non-interactive')
        
        if csv_file:
            command.extend(['--file', csv_file])
        else:
            command.extend(['--hostname', hostname, '--ip', ip])
        
        return self._run_command(command, "Host vars file generation", interactive=not non_interactive)
    
    def provision(self, csv_file: Optional[str], hostname: Optional[str],
                 mac: Optional[str], ip: Optional[str], domain: str,
                 non_interactive: bool, skip_nautobot: bool, skip_dns: bool,
                 skip_dhcp: bool, skip_deploy: bool, skip_hostvars: bool,
                 nautobot_url: Optional[str] = None, nautobot_token: Optional[str] = None,
                 verify_ssl: bool = True, inventory_file: Optional[str] = None) -> bool:
        """Execute the complete provisioning workflow."""
        logger.info("=" * 70)
        logger.info("Mac Provisioning Manager - Starting Workflow")
        logger.info("=" * 70)
        
        results = {
            'nautobot': None,
            'dns': None,
            'dhcp': None,
            'deploy': None,
            'hostvars': None
        }
        
        # Step 1: Add IP to Nautobot
        if not skip_nautobot:
            logger.info("\n[Step 1/5] Adding IP addresses to Nautobot...")
            results['nautobot'] = self.provision_nautobot(
                csv_file, hostname, ip, 'add', nautobot_url, nautobot_token, verify_ssl
            )
            if not results['nautobot']:
                logger.error("Nautobot IP management failed. Continuing with remaining steps...")
        else:
            logger.info("\n[Step 1/5] Skipping Nautobot IP management (--skip-nautobot)")
            results['nautobot'] = True
        
        # Step 2: Create DNS records
        if not skip_dns:
            logger.info("\n[Step 2/5] Creating DNS A records...")
            short_hostname = hostname.split('.')[0] if hostname and '.' in hostname else hostname
            results['dns'] = self.provision_dns(
                csv_file, short_hostname, ip, domain, non_interactive
            )
            if not results['dns']:
                logger.error("DNS record creation failed. Continuing with remaining steps...")
        else:
            logger.info("\n[Step 2/5] Skipping DNS record creation (--skip-dns)")
            results['dns'] = True
        
        # Step 3: Create DHCP reservations
        if not skip_dhcp:
            logger.info("\n[Step 3/5] Creating DHCP reservations...")
            results['dhcp'] = self.provision_dhcp(
                csv_file, hostname, mac, ip, non_interactive
            )
            if not results['dhcp']:
                logger.error("DHCP reservation creation failed. Continuing with remaining steps...")
        else:
            logger.info("\n[Step 3/5] Skipping DHCP reservation creation (--skip-dhcp)")
            results['dhcp'] = True
        
        # Step 4: Deploy DHCP configuration
        if not skip_deploy:
            logger.info("\n[Step 4/5] Deploying DHCP configuration...")
            results['deploy'] = self.deploy_dhcp(inventory_file)
            if not results['deploy']:
                logger.error("DHCP deployment failed. Continuing with remaining steps...")
        else:
            logger.info("\n[Step 4/5] Skipping DHCP deployment (--skip-deploy)")
            results['deploy'] = True
        
        # Step 5: Generate host_vars files
        if not skip_hostvars:
            logger.info("\n[Step 5/5] Generating Ansible host_vars files...")
            results['hostvars'] = self.generate_host_vars(csv_file, hostname, ip, non_interactive)
            if not results['hostvars']:
                logger.error("Host vars generation failed.")
        else:
            logger.info("\n[Step 5/5] Skipping host_vars generation (--skip-hostvars)")
            results['hostvars'] = True
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("Provisioning Workflow Summary")
        logger.info("=" * 70)
        
        for step, success in results.items():
            if success is None:
                continue
            status = "✓ SUCCESS" if success else "✗ FAILED"
            logger.info(f"{step.upper():12} : {status}")
        
        all_successful = all(r for r in results.values() if r is not None)
        
        if all_successful:
            logger.info("\n✓ All provisioning steps completed successfully!")
        else:
            logger.warning("\n⚠ Some provisioning steps failed. Review the logs above.")
        
        return all_successful


def validate_ip(ip: str) -> bool:
    """Validate IP address format."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except (ValueError, TypeError):
        return False


def validate_mac(mac: str) -> bool:
    """Validate MAC address format."""
    import re
    mac = mac.strip().lower().replace('-', ':')
    return bool(re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", mac))


def normalize_mac_address(mac: str) -> Optional[str]:
    """Normalize and validate MAC address."""
    import re
    mac = mac.strip().lower().replace('-', ':')
    if re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", mac):
        return mac
    return None


def parse_csv(file_path: str) -> List[Tuple[str, str, str]]:
    """Parse CSV file in unified format: hostname (FQDN), mac, ip."""
    return parse_mac_ip_csv(
        file_path=file_path,
        mac_validator=normalize_mac_address,
        ip_validator=validate_ip
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Mac Provisioning Manager - Orchestrate DNS, DHCP, and Ansible provisioning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  Provision a single Mac:
    %(prog)s --hostname build-mac-01.macfarm.example.com --mac 00:11:22:33:44:55 --ip 10.0.0.100 --domain macfarm.example.com

  Batch provision from CSV:
    %(prog)s --file hosts.csv --domain macfarm.example.com

  Skip specific steps:
    %(prog)s --file hosts.csv --domain macfarm.example.com --skip-deploy

  Non-interactive mode (for automation):
    %(prog)s --file hosts.csv --domain macfarm.example.com --non-interactive

CSV File Format (unified):
  hostname,mac,ip
  build-mac-01.macfarm.example.com,00:11:22:33:44:55,10.0.0.100
  build-mac-02.macfarm.example.com,00:11:22:33:44:56,10.0.0.101

Workflow Steps:
  1. Add IP addresses to Nautobot (optional)
  2. Create DNS A records (PowerDNS)
  3. Create DHCP reservations
  4. Deploy DHCP configuration (Ansible)
  5. Generate Ansible host_vars files

Environment Variables:
  NAUTOBOT_URL        Nautobot server URL
  NAUTOBOT_TOKEN      Nautobot API token
  POWERDNS_API_KEY    PowerDNS API key (required for DNS operations)
  POWERDNS_SERVER_URL PowerDNS server URL (default: http://localhost:8084)
  DHCPD_CONF_PATH     Path to dhcpd.conf file
  DHCPD_DOMAIN        Domain for DHCP (default: macfarm.example.com)
        '''
    )
    
    # Input options
    input_group = parser.add_argument_group('Input Options')
    input_group.add_argument('--hostname', type=str, help='FQDN hostname')
    input_group.add_argument('--mac', type=str, help='MAC address')
    input_group.add_argument('--ip', type=str, help='IP address')
    input_group.add_argument('--file', type=str, help='CSV file with hostname,mac,ip')
    
    # Configuration options
    config_group = parser.add_argument_group('Configuration Options')
    config_group.add_argument('--domain', type=str, required=True, help='DNS domain')
    config_group.add_argument('--inventory', type=str, help='Ansible inventory file')
    config_group.add_argument('--nautobot-url', type=str, help='Nautobot server URL')
    config_group.add_argument('--nautobot-token', type=str, help='Nautobot API token')
    config_group.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL verification')
    
    # Workflow control
    workflow_group = parser.add_argument_group('Workflow Control')
    workflow_group.add_argument('--skip-nautobot', action='store_true', help='Skip Nautobot')
    workflow_group.add_argument('--skip-dns', action='store_true', help='Skip DNS')
    workflow_group.add_argument('--skip-dhcp', action='store_true', help='Skip DHCP')
    workflow_group.add_argument('--skip-deploy', action='store_true', help='Skip DHCP deployment')
    workflow_group.add_argument('--skip-hostvars', action='store_true', help='Skip host_vars')
    
    # Execution options
    exec_group = parser.add_argument_group('Execution Options')
    exec_group.add_argument('--action', type=str, default='add', choices=['add', 'remove'], help='Action')
    exec_group.add_argument('--non-interactive', action='store_true', help='Non-interactive mode')
    exec_group.add_argument('--debug', action='store_true', help='Debug logging')
    
    return parser.parse_args()


def main() -> int:
    """Main execution function."""
    args = parse_arguments()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input
    if args.file:
        if args.hostname or args.mac or args.ip:
            logger.warning("Both --file and individual arguments provided. Using --file.")
        
        if not os.path.isfile(args.file):
            logger.error(f"CSV file not found: {args.file}")
            return 1
        
        try:
            records = parse_csv(args.file)
            logger.info(f"Loaded {len(records)} valid record(s) from CSV file")
        except Exception as e:
            logger.error(f"Failed to parse CSV file: {e}")
            return 1
    else:
        if not args.hostname:
            logger.error("--hostname is required when not using --file")
            return 1
        if not args.mac:
            logger.error("--mac is required when not using --file")
            return 1
        if not args.ip:
            logger.error("--ip is required when not using --file")
            return 1
        
        if not validate_mac(args.mac):
            logger.error(f"Invalid MAC address format: {args.mac}")
            return 1
        
        if not validate_ip(args.ip):
            logger.error(f"Invalid IP address format: {args.ip}")
            return 1
    
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    ansible_dir = os.path.abspath(os.path.join(scripts_dir, '..', 'ansible'))
    
    try:
        manager = MacProvisioningManager(scripts_dir, ansible_dir)
        
        success = manager.provision(
            csv_file=args.file,
            hostname=args.hostname,
            mac=args.mac,
            ip=args.ip,
            domain=args.domain,
            non_interactive=args.non_interactive,
            skip_nautobot=args.skip_nautobot,
            skip_dns=args.skip_dns,
            skip_dhcp=args.skip_dhcp,
            skip_deploy=args.skip_deploy,
            skip_hostvars=args.skip_hostvars,
            nautobot_url=args.nautobot_url,
            nautobot_token=args.nautobot_token,
            verify_ssl=not args.no_verify_ssl,
            inventory_file=args.inventory
        )
        
        return 0 if success else 1
        
    except FileNotFoundError as e:
        logger.error(f"Dependency error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

