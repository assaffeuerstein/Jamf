#!/usr/bin/env python3
"""
Nautobot IP Address Manager

This script manages IP addresses in Nautobot via the REST API.
It supports adding and removing IP addresses within IP prefixes.
"""

import argparse
import csv
import json
import logging
import sys
from typing import Dict, List, Optional, Tuple
import os

try:
    import pynautobot
except ImportError:
    print("Error: 'pynautobot' module is required. Install it with: pip install pynautobot")
    sys.exit(1)

try:
    import requests
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
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


class NautobotManager:
    """Manages Nautobot IP addresses via REST API."""
    
    def __init__(self, url: str, token: str, verify_ssl: bool = True):
        """
        Initialize Nautobot Manager.
        
        Args:
            url: Nautobot server URL
            token: Nautobot API token for authentication
            verify_ssl: Verify SSL certificates (default: True)
        """
        self.url = url.rstrip('/')
        self.token = token
        self.verify_ssl = verify_ssl
        
        try:
            self.api = pynautobot.api(
                url=self.url,
                token=self.token,
                verify=self.verify_ssl
            )
            logger.debug(f"Connected to Nautobot at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Nautobot: {e}")
            raise
    
    def find_prefix_for_ip(self, ip_address: str) -> Optional[Dict]:
        """Find the IP prefix that contains the given IP address."""
        try:
            logger.debug(f"Searching for prefix containing {ip_address}...")
            
            ip_parts = [int(p) for p in ip_address.split('.')]
            ip_int = (ip_parts[0] << 24) + (ip_parts[1] << 16) + (ip_parts[2] << 8) + ip_parts[3]
            
            prefixes = self.api.ipam.prefixes.all()
            
            best_match = None
            best_match_size = 0
            
            for prefix in prefixes:
                prefix_str = str(prefix.prefix)
                if '/' not in prefix_str:
                    continue
                
                if ':' in prefix_str:
                    logger.debug(f"Skipping IPv6 prefix: {prefix_str}")
                    continue
                    
                try:
                    network, prefix_len = prefix_str.split('/')
                    prefix_len = int(prefix_len)
                    
                    net_parts = network.split('.')
                    if len(net_parts) != 4:
                        continue
                    
                    net_parts = [int(p) for p in net_parts]
                    net_int = (net_parts[0] << 24) + (net_parts[1] << 16) + (net_parts[2] << 8) + net_parts[3]
                    
                    mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
                    
                    if (ip_int & mask) == (net_int & mask):
                        if prefix_len > best_match_size:
                            best_match = prefix
                            best_match_size = prefix_len
                            logger.debug(f"Found matching prefix: {prefix_str}")
                
                except (ValueError, IndexError) as e:
                    logger.debug(f"Error parsing prefix {prefix_str}: {e}")
                    continue
            
            if best_match:
                logger.info(f"Found prefix: {best_match.prefix} (ID: {best_match.id})")
                return best_match
            else:
                logger.warning(f"No IPv4 prefix found containing IP {ip_address}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching for prefix: {e}")
            return None
    
    def get_ip_address(self, ip_address: str) -> Optional[Dict]:
        """Get IP address object from Nautobot."""
        try:
            ip_objects = self.api.ipam.ip_addresses.filter(address=ip_address)
            if ip_objects:
                return ip_objects[0]
            return None
        except Exception as e:
            logger.error(f"Error retrieving IP address: {e}")
            return None
    
    def add_ip_address(self, ip_address: str, hostname: str = None, 
                      description: str = None, dry_run: bool = False) -> bool:
        """Add an IP address to Nautobot."""
        try:
            existing_ip = self.get_ip_address(f"{ip_address}/32")
            
            if existing_ip:
                logger.info(f"IP address {ip_address} already exists in Nautobot")
                
                needs_update = False
                update_data = {}
                
                if hostname and getattr(existing_ip, 'dns_name', None) != hostname:
                    needs_update = True
                    update_data['dns_name'] = hostname
                
                target_description = description if description else hostname
                if target_description and getattr(existing_ip, 'description', None) != target_description:
                    needs_update = True
                    update_data['description'] = target_description
                
                if needs_update:
                    if dry_run:
                        logger.info(f"[DRY RUN] Would update IP address {ip_address}")
                        return True
                    else:
                        existing_ip.update(update_data)
                        logger.info(f"Successfully updated IP address {ip_address}")
                        return True
                else:
                    logger.info(f"IP address {ip_address} is up to date")
                    return True
            
            prefix = self.find_prefix_for_ip(ip_address)
            
            if not prefix:
                logger.error(f"Cannot add IP {ip_address}: no matching prefix found")
                return False
            
            if dry_run:
                logger.info(f"[DRY RUN] Would create IP address {ip_address}")
                return True
            
            ip_data = {
                'address': f"{ip_address}/32",
                'status': 'active'
            }
            
            if hostname:
                ip_data['dns_name'] = hostname
            
            if description:
                ip_data['description'] = description
            elif hostname:
                ip_data['description'] = hostname
            
            if hasattr(prefix, 'vrf') and prefix.vrf:
                ip_data['vrf'] = prefix.vrf.id
            
            if hasattr(prefix, 'namespace') and prefix.namespace:
                ip_data['namespace'] = prefix.namespace.id
            
            if hasattr(prefix, 'tenant') and prefix.tenant:
                ip_data['tenant'] = prefix.tenant.id
            
            logger.info(f"Creating IP address {ip_address}...")
            new_ip = self.api.ipam.ip_addresses.create(**ip_data)
            logger.info(f"Successfully created IP address {ip_address} (ID: {new_ip.id})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add IP address {ip_address}: {e}")
            return False
    
    def remove_ip_address(self, ip_address: str, dry_run: bool = False) -> bool:
        """Remove an IP address from Nautobot."""
        try:
            existing_ip = self.get_ip_address(f"{ip_address}/32")
            
            if not existing_ip:
                logger.warning(f"IP address {ip_address} does not exist in Nautobot")
                return False
            
            logger.info(f"Found IP address to remove: {ip_address}")
            
            if dry_run:
                logger.info(f"[DRY RUN] Would delete IP address {ip_address}")
                return True
            
            existing_ip.delete()
            logger.info(f"Successfully deleted IP address {ip_address}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove IP address {ip_address}: {e}")
            return False


def validateIpAddress(ip_address: str) -> bool:
    """Validate IP address format."""
    parts = ip_address.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except (ValueError, TypeError):
        return False


def parseCsvFile(file_path: str) -> List[Tuple[str, str]]:
    """Parse CSV file with hostname and IP address."""
    records = []
    
    try:
        with open(file_path, 'r') as csvfile:
            lines = csvfile.readlines()
            lines = [line.strip() for line in lines if line.strip()]
            
            if not lines:
                raise ValueError("CSV file is empty")
            
            first_line = lines[0].lower()
            has_header = any(keyword in first_line for keyword in [
                'hostname', 'host', 'name', 'ip', 'address', 'mac'
            ]) and not validateIpAddress(first_line.split(',')[-1].strip())
            
            start_line = 1 if has_header else 0
            
            if has_header and len(lines) == 1:
                raise ValueError("CSV file contains only a header row")
            
            reader = csv.reader(lines[start_line:])
            
            for line_num, row in enumerate(reader, start=start_line + 1):
                if not row or all(not cell.strip() for cell in row):
                    continue
                
                if len(row) == 2:
                    hostname = row[0].strip()
                    ip_address = row[1].strip()
                elif len(row) >= 3:
                    hostname = row[0].strip()
                    ip_address = row[2].strip()
                else:
                    logger.warning(f"Line {line_num}: Invalid format, skipping")
                    continue
                
                if not hostname or not ip_address:
                    continue
                
                if not validateIpAddress(ip_address):
                    logger.warning(f"Line {line_num}: Invalid IP address '{ip_address}', skipping")
                    continue
                
                records.append((hostname, ip_address))
        
        if not records:
            raise ValueError("No valid records found in CSV file")
        
        logger.info(f"Loaded {len(records)} record(s) from CSV file")
        return records
        
    except FileNotFoundError:
        raise ValueError(f"CSV file not found: {file_path}")
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")


def parseArguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Manage IP addresses in Nautobot via REST API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Add a single IP address:
    %(prog)s --hostname server01 --ip 192.168.1.100 --action add
    
  Remove a single IP address:
    %(prog)s --hostname server01 --ip 192.168.1.100 --action remove
    
  Batch add IP addresses from CSV file:
    %(prog)s --file hosts.csv --action add
    
  Test changes without applying them (dry-run):
    %(prog)s --file hosts.csv --action add --dry-run

Environment Variables:
  NAUTOBOT_URL      Nautobot server URL (required if not using --url)
  NAUTOBOT_TOKEN    Nautobot API token (required if not using --token)
        """
    )
    
    parser.add_argument('--hostname', type=str, help='Hostname')
    parser.add_argument('--ip', type=str, help='IP address')
    parser.add_argument('--file', type=str, help='CSV file for batch operations')
    parser.add_argument('--action', type=str, required=True, choices=['add', 'remove'], help='Action')
    parser.add_argument('--url', type=str, help='Nautobot server URL')
    parser.add_argument('--token', type=str, help='Nautobot API token')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL verification')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    return parser.parse_args()


def main() -> int:
    """Main execution function."""
    args = parseArguments()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 60)
    
    if args.file:
        if args.hostname or args.ip:
            logger.warning("Both --file and --hostname/--ip provided. Using --file.")
        
        try:
            records = parseCsvFile(args.file)
        except ValueError as e:
            logger.error(f"CSV file error: {e}")
            return 1
    else:
        if not args.hostname:
            logger.error("--hostname is required when not using --file")
            return 1
        if not args.ip:
            logger.error("--ip is required when not using --file")
            return 1
        
        if not validateIpAddress(args.ip):
            logger.error(f"Invalid IP address format: {args.ip}")
            return 1
        
        records = [(args.hostname, args.ip)]
    
    url = args.url or os.environ.get('NAUTOBOT_URL')
    if not url:
        logger.error("Nautobot URL not provided. Use --url or set NAUTOBOT_URL")
        return 1
    
    token = args.token or os.environ.get('NAUTOBOT_TOKEN')
    if not token:
        logger.error("Nautobot token not provided. Use --token or set NAUTOBOT_TOKEN")
        return 1
    
    verify_ssl = not args.no_verify_ssl
    
    try:
        nautobot = NautobotManager(url=url, token=token, verify_ssl=verify_ssl)
    except Exception as e:
        logger.error(f"Failed to initialize Nautobot manager: {e}")
        return 1
    
    total_records = len(records)
    successful = 0
    failed = 0
    
    logger.info(f"Processing {total_records} record(s)...")
    
    for hostname, ip_address in records:
        logger.info(f"Processing: {hostname} -> {ip_address}")
        
        success = False
        if args.action == 'add':
            success = nautobot.add_ip_address(
                ip_address=ip_address,
                hostname=hostname,
                dry_run=args.dry_run
            )
        elif args.action == 'remove':
            success = nautobot.remove_ip_address(
                ip_address=ip_address,
                dry_run=args.dry_run
            )
        
        if success:
            successful += 1
        else:
            failed += 1
    
    logger.info("=" * 60)
    logger.info(f"Summary: {successful} successful, {failed} failed")
    logger.info("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

