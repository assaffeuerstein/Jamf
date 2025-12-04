#!/usr/bin/env python3
"""
Mac Inventory Collector

SSH into existing Mac Mini machines to collect inventory information
(MAC addresses and hostnames) and generate a CSV file compatible
with the provisioning workflow.
"""

import argparse
import csv
import ipaddress
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def parse_ip_range(ip_spec: str) -> List[str]:
    """
    Parse an IP specification into a list of IP addresses.
    
    Supported formats:
    - Single IP: 10.0.0.10
    - IP range (last octet): 10.0.0.10-20
    - IP range (full): 10.0.0.10-10.0.0.20
    - CIDR: 10.0.0.0/28
    
    Args:
        ip_spec: IP specification string
        
    Returns:
        List of IP addresses as strings
    """
    ips = []
    
    # Check for CIDR notation
    if '/' in ip_spec:
        try:
            network = ipaddress.ip_network(ip_spec, strict=False)
            for ip in network.hosts():
                ips.append(str(ip))
            return ips
        except ValueError as e:
            raise ValueError(f"Invalid CIDR notation: {ip_spec}") from e
    
    # Check for range notation
    if '-' in ip_spec:
        parts = ip_spec.split('-')
        if len(parts) != 2:
            raise ValueError(f"Invalid IP range: {ip_spec}")
        
        start = parts[0].strip()
        end = parts[1].strip()
        
        # Check if end is just the last octet
        if '.' not in end:
            # Last octet range: 10.0.0.10-20
            base = '.'.join(start.split('.')[:-1])
            start_last = int(start.split('.')[-1])
            end_last = int(end)
            
            for i in range(start_last, end_last + 1):
                ips.append(f"{base}.{i}")
        else:
            # Full IP range: 10.0.0.10-10.0.0.20
            start_ip = ipaddress.ip_address(start)
            end_ip = ipaddress.ip_address(end)
            
            current = start_ip
            while current <= end_ip:
                ips.append(str(current))
                current = ipaddress.ip_address(int(current) + 1)
        
        return ips
    
    # Single IP
    try:
        ipaddress.ip_address(ip_spec)
        return [ip_spec]
    except ValueError as e:
        raise ValueError(f"Invalid IP address: {ip_spec}") from e


def collect_mac_info(ip: str, user: str, key_path: Optional[str], timeout: int) -> Optional[Tuple[str, str, str]]:
    """
    Collect MAC address and hostname from a remote Mac via SSH.
    
    Args:
        ip: IP address of the Mac
        user: SSH username
        key_path: Path to SSH private key (optional)
        timeout: SSH connection timeout in seconds
        
    Returns:
        Tuple of (hostname, mac_address, ip) if successful, None otherwise
    """
    try:
        logger.info(f"Collecting info from {ip}...")
        
        # Build SSH command
        ssh_cmd = [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', f'ConnectTimeout={timeout}',
            '-o', 'BatchMode=yes',
        ]
        
        if key_path:
            ssh_cmd.extend(['-i', key_path])
        
        ssh_cmd.append(f"{user}@{ip}")
        
        # Get hostname
        hostname_cmd = ssh_cmd + ['hostname']
        hostname_result = subprocess.run(
            hostname_cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5
        )
        
        if hostname_result.returncode != 0:
            logger.warning(f"Failed to get hostname from {ip}: {hostname_result.stderr.strip()}")
            return None
        
        hostname = hostname_result.stdout.strip()
        
        # Get MAC address from en0 (primary Ethernet interface)
        mac_cmd = ssh_cmd + ["ifconfig en0 | grep ether | awk '{print $2}'"]
        mac_result = subprocess.run(
            mac_cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            shell=False
        )
        
        # Alternative: try using networksetup if ifconfig fails
        if mac_result.returncode != 0 or not mac_result.stdout.strip():
            mac_cmd = ssh_cmd + ["networksetup -getmacaddress Ethernet | awk '{print $3}'"]
            mac_result = subprocess.run(
                mac_cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
        
        if mac_result.returncode != 0 or not mac_result.stdout.strip():
            logger.warning(f"Failed to get MAC address from {ip}")
            return None
        
        mac_address = mac_result.stdout.strip().lower()
        
        logger.info(f"✓ {ip}: {hostname} ({mac_address})")
        return (hostname, mac_address, ip)
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout connecting to {ip}")
        return None
    except Exception as e:
        logger.warning(f"Error connecting to {ip}: {e}")
        return None


def write_csv(records: List[Tuple[str, str, str]], output_path: str) -> None:
    """
    Write collected records to a CSV file.
    
    Args:
        records: List of (hostname, mac, ip) tuples
        output_path: Path to output CSV file
    """
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['hostname', 'mac', 'ip'])
        for record in records:
            writer.writerow(record)
    
    logger.info(f"✓ CSV file created: {output_path}")
    logger.info(f"  Total records: {len(records)}")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Collect inventory from existing Mac machines via SSH',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  Collect from single IP:
    %(prog)s --ip 10.0.0.100

  Collect from IP range:
    %(prog)s --ip 10.0.0.100-120

  Collect from CIDR:
    %(prog)s --ip 10.0.0.0/28

  Collect with custom output:
    %(prog)s --ip 10.0.0.100-120 --output /tmp/inventory.csv

  Collect with custom SSH user:
    %(prog)s --ip 10.0.0.100-120 --user admin

Output Format:
  hostname,mac,ip
  build-mac-01.macfarm.example.com,00:11:22:33:44:55,10.0.0.100
        '''
    )
    
    ip_group = parser.add_mutually_exclusive_group(required=True)
    ip_group.add_argument(
        '--ip',
        type=str,
        nargs='+',
        help='IP address(es) or range(s)'
    )
    ip_group.add_argument(
        '--start-ip',
        type=str,
        help='Start IP address (requires --end-ip)'
    )
    
    parser.add_argument(
        '--end-ip',
        type=str,
        help='End IP address (requires --start-ip)'
    )
    
    parser.add_argument(
        '--user',
        type=str,
        default='buildadmin',
        help='SSH username (default: buildadmin)'
    )
    
    parser.add_argument(
        '--key',
        type=str,
        help='Path to SSH private key'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV file path (default: /tmp/mac_inventory_YYYYMMDD_HHMMSS.csv)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=10,
        help='SSH connection timeout in seconds (default: 10)'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=10,
        help='Maximum parallel SSH connections (default: 10)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser.parse_args()


def main() -> int:
    """Main execution function."""
    args = parse_arguments()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse IP addresses
    all_ips = []
    
    if args.start_ip:
        if not args.end_ip:
            logger.error("--end-ip is required when using --start-ip")
            return 1
        
        try:
            ip_range = f"{args.start_ip}-{args.end_ip}"
            all_ips = parse_ip_range(ip_range)
        except ValueError as e:
            logger.error(str(e))
            return 1
    else:
        for ip_spec in args.ip:
            try:
                ips = parse_ip_range(ip_spec)
                all_ips.extend(ips)
            except ValueError as e:
                logger.error(str(e))
                return 1
    
    # Remove duplicates while preserving order
    seen = set()
    unique_ips = []
    for ip in all_ips:
        if ip not in seen:
            seen.add(ip)
            unique_ips.append(ip)
    
    logger.info(f"Total IPs to process: {len(unique_ips)}")
    logger.info(f"Starting inventory collection for {len(unique_ips)} host(s)...")
    logger.info(f"Using SSH user: {args.user}")
    logger.info(f"Max parallel connections: {args.max_workers}")
    logger.info("=" * 70)
    
    # Collect inventory in parallel
    records = []
    failed = []
    
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_ip = {
            executor.submit(
                collect_mac_info,
                ip,
                args.user,
                args.key,
                args.timeout
            ): ip
            for ip in unique_ips
        }
        
        for future in as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                result = future.result()
                if result:
                    records.append(result)
                else:
                    failed.append(ip)
            except Exception as e:
                logger.error(f"Exception processing {ip}: {e}")
                failed.append(ip)
    
    logger.info("=" * 70)
    logger.info(f"Collection complete: {len(records)} successful, {len(failed)} failed")
    
    if not records:
        logger.error("No records collected. Cannot create CSV file.")
        return 1
    
    # Generate output path
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"/tmp/mac_inventory_{timestamp}.csv"
    
    # Write CSV
    write_csv(records, output_path)
    
    logger.info("")
    logger.info("To provision these machines, run:")
    logger.info(f"  ./mac_provisioning_manager.py --file {output_path} --domain <domain>")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

