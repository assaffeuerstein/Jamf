#!/usr/bin/env python3
"""
PowerDNS A Record Manager

This script manages A records in PowerDNS via the REST API.
It supports adding and removing A records for specified hostnames.
"""

import argparse
import csv
import json
import logging
import sys
from typing import Dict, List, Optional, Tuple
import os

# Import shared CSV parsing utility
from csv_utils import parse_mac_ip_csv

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("Error: 'requests' module is required. Install it with: pip install requests")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class PowerDNSManager:
    """Manages PowerDNS A records via REST API."""
    
    def __init__(self, server_url: str, api_key: str, server_id: str = "localhost"):
        """
        Initialize PowerDNS Manager.
        
        Args:
            server_url: PowerDNS API base URL
            api_key: PowerDNS API key for authentication
            server_id: PowerDNS server ID (default: localhost)
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.server_id = server_id
        self.api_base = f"{self.server_url}/api/v1/servers/{self.server_id}"
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic.
        
        Returns:
            Configured requests session
        """
        session = requests.Session()
        session.headers.update({
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        })
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "PATCH"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_zone_endpoint(self, domain: str) -> str:
        """
        Get the zone endpoint URL.
        
        Args:
            domain: Domain name
            
        Returns:
            Zone endpoint URL
        """
        return f"{self.api_base}/zones/{domain}"
    
    def _ensure_fqdn(self, hostname: str, domain: str) -> str:
        """
        Ensure hostname is a fully qualified domain name.
        
        Args:
            hostname: Hostname
            domain: Domain name
            
        Returns:
            Fully qualified domain name with trailing dot
        """
        if not hostname.endswith(domain):
            fqdn = f"{hostname}.{domain}"
        else:
            fqdn = hostname
            
        if not fqdn.endswith('.'):
            fqdn += '.'
            
        return fqdn
    
    def _get_existing_records(self, domain: str, fqdn: str) -> List[str]:
        """
        Get existing A records for a hostname.
        
        Args:
            domain: Domain name
            fqdn: Fully qualified domain name
            
        Returns:
            List of existing IP addresses
        """
        try:
            zone_endpoint = self._get_zone_endpoint(domain)
            response = self.session.get(zone_endpoint, verify=False)
            response.raise_for_status()
            
            zone_data = response.json()
            rrsets = zone_data.get('rrsets', [])
            
            for rrset in rrsets:
                if rrset['name'] == fqdn and rrset['type'] == 'A':
                    return [record['content'] for record in rrset.get('records', [])]
            
            return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve existing records: {e}")
            return []
    
    def _find_hostname_by_ip(self, domain: str, ip_address: str) -> Optional[str]:
        """
        Find the hostname that has an A record pointing to the specified IP.
        
        Args:
            domain: Domain name
            ip_address: IP address to search for
            
        Returns:
            Hostname (FQDN) if found, None otherwise
        """
        try:
            zone_endpoint = self._get_zone_endpoint(domain)
            response = self.session.get(zone_endpoint, verify=False)
            response.raise_for_status()
            
            zone_data = response.json()
            rrsets = zone_data.get('rrsets', [])
            
            for rrset in rrsets:
                if rrset['type'] == 'A':
                    for record in rrset.get('records', []):
                        if record['content'] == ip_address:
                            return rrset['name']
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search for hostname by IP: {e}")
            return None
    
    def add_record(self, domain: str, hostname: str, ip_address: str, ttl: int = 3600, 
                   interactive: bool = True) -> bool:
        """
        Add an A record to PowerDNS.
        
        Args:
            domain: Domain name
            hostname: Hostname to add
            ip_address: IP address for the A record
            ttl: Time to live (default: 3600)
            interactive: If True, prompt user for confirmation on conflicts (default: True)
            
        Returns:
            True if successful, False otherwise
        """
        fqdn = self._ensure_fqdn(hostname, domain)
        zone_endpoint = self._get_zone_endpoint(domain)
        
        # Check if this IP is already assigned to another hostname
        existing_hostname = self._find_hostname_by_ip(domain, ip_address)
        
        if existing_hostname:
            # IP is already in use
            if existing_hostname == fqdn:
                # Same hostname and IP - already exists, nothing to do
                logger.info(f"Record {fqdn} -> {ip_address} already exists, skipping")
                return True
            else:
                # Different hostname has this IP - conflict detected
                logger.warning(f"IP {ip_address} is already assigned to {existing_hostname}")
                
                if interactive:
                    response = getUserConfirmation(
                        f"Do you want to remove {existing_hostname} -> {ip_address} and add {fqdn} -> {ip_address}?"
                    )
                    if not response:
                        logger.info(f"Skipping record: {fqdn} -> {ip_address}")
                        return False
                else:
                    logger.error(f"Conflict: IP {ip_address} is already used by {existing_hostname}. "
                               f"Run in interactive mode to resolve conflicts.")
                    return False
                
                # Remove the old record first
                logger.info(f"Removing conflicting record: {existing_hostname} -> {ip_address}")
                if not self._remove_ip_from_hostname(domain, existing_hostname, ip_address):
                    logger.error(f"Failed to remove conflicting record")
                    return False
        
        # Get existing records for this hostname
        existing_ips = self._get_existing_records(domain, fqdn)
        
        if ip_address in existing_ips:
            logger.info(f"Record {fqdn} -> {ip_address} already exists")
            return True
        
        # Add the new IP to existing ones
        all_ips = existing_ips + [ip_address]
        records = [{"content": ip, "disabled": False} for ip in all_ips]
        
        rrset_data = {
            "rrsets": [
                {
                    "name": fqdn,
                    "type": "A",
                    "ttl": ttl,
                    "changetype": "REPLACE",
                    "records": records
                }
            ]
        }
        
        try:
            response = self.session.patch(zone_endpoint, json=rrset_data, verify=False)
            response.raise_for_status()
            logger.info(f"Successfully added A record: {fqdn} -> {ip_address}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add A record: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return False
    
    def _remove_ip_from_hostname(self, domain: str, fqdn: str, ip_address: str) -> bool:
        """
        Remove a specific IP from a hostname's A records.
        
        Args:
            domain: Domain name
            fqdn: Fully qualified domain name (with trailing dot)
            ip_address: IP address to remove
            
        Returns:
            True if successful, False otherwise
        """
        zone_endpoint = self._get_zone_endpoint(domain)
        
        # Get existing records
        existing_ips = self._get_existing_records(domain, fqdn)
        
        if ip_address not in existing_ips:
            logger.warning(f"IP {ip_address} not found in {fqdn}")
            return False
        
        # Remove the IP from existing ones
        remaining_ips = [ip for ip in existing_ips if ip != ip_address]
        
        if remaining_ips:
            # Update with remaining IPs
            records = [{"content": ip, "disabled": False} for ip in remaining_ips]
            rrset_data = {
                "rrsets": [
                    {
                        "name": fqdn,
                        "type": "A",
                        "changetype": "REPLACE",
                        "records": records
                    }
                ]
            }
        else:
            # Delete the entire record if no IPs remain
            rrset_data = {
                "rrsets": [
                    {
                        "name": fqdn,
                        "type": "A",
                        "changetype": "DELETE"
                    }
                ]
            }
        
        try:
            response = self.session.patch(zone_endpoint, json=rrset_data, verify=False)
            response.raise_for_status()
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to remove IP from hostname: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return False
    
    def remove_record(self, domain: str, hostname: str, ip_address: Optional[str] = None) -> bool:
        """
        Remove an A record from PowerDNS.
        
        If ip_address is provided, removes only that specific IP.
        If ip_address is None, removes all A records for the hostname.
        
        Args:
            domain: Domain name
            hostname: Hostname to remove
            ip_address: IP address to remove (optional - if None, removes all A records)
            
        Returns:
            True if successful, False otherwise
        """
        fqdn = self._ensure_fqdn(hostname, domain)
        zone_endpoint = self._get_zone_endpoint(domain)
        
        # Get existing records
        existing_ips = self._get_existing_records(domain, fqdn)
        
        if not existing_ips:
            logger.warning(f"No A records found for {fqdn}")
            return False
        
        # If no specific IP provided, remove all records
        if ip_address is None:
            logger.info(f"Removing all A records for {fqdn} (IPs: {', '.join(existing_ips)})")
            rrset_data = {
                "rrsets": [
                    {
                        "name": fqdn,
                        "type": "A",
                        "changetype": "DELETE"
                    }
                ]
            }
        else:
            # Remove specific IP
            if ip_address not in existing_ips:
                logger.warning(f"Record {fqdn} -> {ip_address} does not exist")
                return False
            
            # Remove the IP from existing ones
            remaining_ips = [ip for ip in existing_ips if ip != ip_address]
            
            if remaining_ips:
                # Update with remaining IPs
                records = [{"content": ip, "disabled": False} for ip in remaining_ips]
                rrset_data = {
                    "rrsets": [
                        {
                            "name": fqdn,
                            "type": "A",
                            "changetype": "REPLACE",
                            "records": records
                        }
                    ]
                }
            else:
                # Delete the entire record if no IPs remain
                rrset_data = {
                    "rrsets": [
                        {
                            "name": fqdn,
                            "type": "A",
                            "changetype": "DELETE"
                        }
                    ]
                }
        
        try:
            response = self.session.patch(zone_endpoint, json=rrset_data, verify=False)
            response.raise_for_status()
            
            if ip_address:
                logger.info(f"Successfully removed A record: {fqdn} -> {ip_address}")
            else:
                logger.info(f"Successfully removed all A records for {fqdn}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to remove A record: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return False


def parseCsvFile(file_path: str) -> List[Tuple[str, str]]:
    """
    Parse CSV file in unified DHCP format: hostname (FQDN), mac, ip.
    Uses robust header detection that works with single-line CSV files.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of tuples containing (short_hostname, ip_address)
        
    Raises:
        ValueError: If CSV file is invalid or cannot be read
    """
    # Parse using shared utility (MAC is validated but not used)
    full_records = parse_mac_ip_csv(
        file_path=file_path,
        mac_validator=None,  # We don't care about MAC validation for DNS
        ip_validator=validateIpAddress
    )
    
    # Convert FQDN to short hostname for DNS and extract only hostname & IP
    records = []
    for fqdn, _mac, ip_address in full_records:
        short_hostname = fqdn.split('.', 1)[0]
        records.append((short_hostname, ip_address))
    
    logger.info(f"Loaded {len(records)} record(s) from CSV file")
    return records


def parseArguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Manage PowerDNS A records via REST API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Add a single record:
    %(prog)s --domain example.com --hostname server01 --ip 192.168.1.100 --action add
    
  Remove a specific IP from a hostname:
    %(prog)s --domain example.com --hostname server01 --ip 192.168.1.100 --action remove
    
  Remove all A records for a hostname:
    %(prog)s --domain example.com --hostname server01 --action remove
    
  Batch add records from CSV file (unified DHCP format):
    %(prog)s --domain example.com --file hosts.csv --action add
    
  Batch remove records from CSV file:
    %(prog)s --domain example.com --file hosts.csv --action remove
    
  Run in non-interactive mode (skip prompts on conflicts):
    %(prog)s --domain example.com --file hosts.csv --action add --non-interactive

CSV File Format (unified):
  The CSV file should contain FQDN hostname, MAC (ignored), and IP:
    hostname,mac,ip
    server01.example.com,00:11:22:33:44:55,192.168.1.100
    server02.example.com,00:11:22:33:44:56,192.168.1.101
    server03.example.com,00:11:22:33:44:57,192.168.1.102
  
  Headers are optional and will be automatically detected.

Conflict Resolution:
  When adding a record, the script checks if the IP is already assigned to another hostname.
  - If the hostname matches, the record is skipped (already exists).
  - If the hostname differs, the script will prompt for confirmation (interactive mode).
  - Use --non-interactive to skip conflicts without prompting.

Environment Variables:
  POWERDNS_API_KEY    PowerDNS API key (required if not using --api-key)
  POWERDNS_SERVER_URL PowerDNS server URL (default: http://localhost:8084)
  POWERDNS_SERVER_ID  PowerDNS server ID (default: localhost)
        """
    )
    
    parser.add_argument(
        '--domain',
        type=str,
        required=True,
        help='Domain name (e.g., example.com)'
    )
    
    parser.add_argument(
        '--hostname',
        type=str,
        help='Hostname to add/remove (e.g., server01). Not required if using --file.'
    )
    
    parser.add_argument(
        '--ip',
        type=str,
        help='IP address for the A record (e.g., 192.168.1.100). Required for add action. Optional for remove action (if not specified, removes all A records for hostname).'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        help='CSV file containing hostname,ipaddress pairs for batch operations. When specified, --hostname and --ip are ignored.'
    )
    
    parser.add_argument(
        '--action',
        type=str,
        required=True,
        choices=['add', 'remove'],
        help='Action to perform: add or remove'
    )
    
    parser.add_argument(
        '--ttl',
        type=int,
        default=3600,
        help='Time to live for the record (default: 3600)'
    )
    
    parser.add_argument(
        '--api-key',
        type=str,
        help='PowerDNS API key (overrides POWERDNS_API_KEY env var)'
    )
    
    parser.add_argument(
        '--server-url',
        type=str,
        help='PowerDNS server URL (default: http://localhost:8084)'
    )
    
    parser.add_argument(
        '--server-id',
        type=str,
        default='localhost',
        help='PowerDNS server ID (default: localhost)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run in non-interactive mode (skip user prompts on conflicts)'
    )
    
    return parser.parse_args()


def validateIpAddress(ip_address: str) -> bool:
    """
    Validate IP address format.
    
    Args:
        ip_address: IP address to validate
        
    Returns:
        True if valid, False otherwise
    """
    parts = ip_address.split('.')
    
    if len(parts) != 4:
        return False
    
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except (ValueError, TypeError):
        return False


def getUserConfirmation(prompt: str) -> bool:
    """
    Prompt user for yes/no confirmation.
    
    Args:
        prompt: Question to ask the user
        
    Returns:
        True if user confirms (yes), False otherwise (no)
    """
    while True:
        try:
            response = input(f"{prompt} (yes/no): ").strip().lower()
            if response in ['yes', 'y']:
                return True
            elif response in ['no', 'n']:
                return False
            else:
                print("Please answer 'yes' or 'no'")
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled by user")
            return False


def main() -> int:
    """
    Main execution function.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    args = parseArguments()
    
    # Configure logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input: either file or hostname must be provided
    if args.file:
        if args.hostname or args.ip:
            logger.warning("Both --file and --hostname/--ip provided. Using --file, ignoring --hostname and --ip.")
        
        # Parse CSV file
        try:
            records = parseCsvFile(args.file)
        except ValueError as e:
            logger.error(f"CSV file error: {e}")
            return 1
    else:
        # Single record mode - validate required parameters
        if not args.hostname:
            logger.error("--hostname is required when not using --file")
            return 1
        
        # For 'add' action, IP is required
        # For 'remove' action, IP is optional (if not provided, removes all A records)
        if args.action == 'add':
            if not args.ip:
                logger.error("--ip is required when adding a record")
                return 1
            
            # Validate IP address
            if not validateIpAddress(args.ip):
                logger.error(f"Invalid IP address format: {args.ip}")
                return 1
        
        elif args.action == 'remove':
            # IP is optional for remove
            if args.ip:
                # Validate IP address if provided
                if not validateIpAddress(args.ip):
                    logger.error(f"Invalid IP address format: {args.ip}")
                    return 1
            else:
                logger.info(f"No IP specified - will remove all A records for {args.hostname}")
        
        records = [(args.hostname, args.ip)]
    
    # Get API key from argument or environment
    api_key = args.api_key or os.environ.get('POWERDNS_API_KEY')
    if not api_key:
        logger.error("PowerDNS API key not provided. Use --api-key or set POWERDNS_API_KEY environment variable")
        return 1
    
    # Get server URL
    server_url = args.server_url or os.environ.get('POWERDNS_SERVER_URL', 'http://localhost:8084')
    
    # Get server ID
    server_id = args.server_id or os.environ.get('POWERDNS_SERVER_ID', 'localhost')
    
    # Suppress SSL warnings for internal servers
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Initialize PowerDNS manager
    pdns = PowerDNSManager(
        server_url=server_url,
        api_key=api_key,
        server_id=server_id
    )
    
    # Process records
    total_records = len(records)
    successful = 0
    failed = 0
    
    # Determine if running in interactive mode
    interactive_mode = not args.non_interactive
    
    logger.info(f"Processing {total_records} record(s)...")
    if not interactive_mode:
        logger.info("Running in non-interactive mode - conflicts will be skipped")
    
    for hostname, ip_address in records:
        if ip_address:
            logger.info(f"Processing: {hostname} -> {ip_address}")
        else:
            logger.info(f"Processing: {hostname} (all A records)")
        
        success = False
        if args.action == 'add':
            success = pdns.add_record(
                domain=args.domain,
                hostname=hostname,
                ip_address=ip_address,
                ttl=args.ttl,
                interactive=interactive_mode
            )
        elif args.action == 'remove':
            success = pdns.remove_record(
                domain=args.domain,
                hostname=hostname,
                ip_address=ip_address
            )
        
        if success:
            successful += 1
        else:
            failed += 1
    
    # Summary
    logger.info(f"Summary: {successful} successful, {failed} failed out of {total_records} record(s)")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

