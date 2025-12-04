#!/usr/bin/env python3
"""
DHCP Reservation Manager

This script adds or removes DHCP reservations in a dhcpd.conf file.
It supports single operations and batch processing via CSV file.

Reservation block format (ISC dhcpd):

host <hostname> {
  hardware ethernet <mac>;
  fixed-address <ip>;
}

Notes:
- Hostname will be treated as a literal identifier (no quotes).
- MAC may include ':' or '-' separators (normalized to ':').
- A domain can be appended to the hostname for FQDN, if desired.
"""

import argparse
import csv
import datetime
import os
import re
import shutil
import subprocess
import sys
from typing import List, Optional, Tuple


DEFAULT_RELATIVE_DHCPD_CONF = os.path.join('..', 'ansible', 'roles', 'dhcpd', 'files', 'dhcpd.conf')


def validate_ip_address(ip: str) -> bool:
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except (ValueError, TypeError):
        return False


def normalize_mac(mac: str) -> Optional[str]:
    mac = mac.strip().lower().replace('-', ':')
    if not re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", mac):
        return None
    return mac


def build_reservation_block(hostname: str, mac: str, ip: str, domain: Optional[str]) -> str:
    fqdn = f"{hostname}.{domain}" if domain and not hostname.endswith(f".{domain}") else hostname
    # Preserve consistent two-space indentation inside block
    return (
        f"host {fqdn} {{\n"
        f"  hardware ethernet {mac};\n"
        f"  fixed-address {ip};\n"
        f"}}\n"
    )


def parse_csv(file_path: str) -> List[Tuple[str, str, str]]:
    records: List[Tuple[str, str, str]] = []
    with open(file_path, 'r') as f:
        # Read the first line to check if it's a header
        first_line = f.readline().strip()
        f.seek(0)
        
        # Determine if there's a header by checking if the first line looks like data
        has_header = False
        if first_line:
            # Try to parse the first line as CSV
            try:
                first_row = next(csv.reader([first_line]))
                if len(first_row) >= 3:
                    # Check if it looks like data (has MAC and IP patterns) or a header
                    potential_mac = first_row[1].strip()
                    potential_ip = first_row[2].strip()
                    
                    # If the second column looks like a MAC and third like an IP, it's data
                    if normalize_mac(potential_mac) and validate_ip_address(potential_ip):
                        has_header = False
                    else:
                        # Otherwise, try the CSV sniffer
                        sample = f.read(1024)
                        f.seek(0)
                        has_header = csv.Sniffer().has_header(sample)
            except Exception:
                # If parsing fails, fall back to sniffer
                sample = f.read(1024)
                f.seek(0)
                try:
                    has_header = csv.Sniffer().has_header(sample)
                except Exception:
                    # If sniffer also fails, assume no header
                    has_header = False
        
        reader = csv.reader(f)
        if has_header:
            next(reader, None)
        
        for idx, row in enumerate(reader, start=2 if has_header else 1):
            # Unified format: hostname (FQDN), mac, ip
            if not row or len(row) < 3:
                print(f"WARNING: CSV line {idx}: expected 'hostname,mac,ip' - skipping")
                continue
            hostname, mac, ip = row[0].strip(), row[1].strip(), row[2].strip()
            norm_mac = normalize_mac(mac)
            if not hostname or not norm_mac or not validate_ip_address(ip):
                print(f"WARNING: CSV line {idx}: invalid hostname/mac/ip - skipping")
                continue
            records.append((hostname, norm_mac, ip))
    if not records:
        raise ValueError("No valid records found in CSV file")
    return records


def load_config_text(config_path: str) -> str:
    with open(config_path, 'r') as f:
        return f.read()


def save_config_text(config_path: str, content: str) -> None:
    with open(config_path, 'w') as f:
        f.write(content)


def make_backup(config_path: str) -> str:
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_path = f"{config_path}.{ts}.bak"
    shutil.copy2(config_path, backup_path)
    return backup_path


def validate_dhcpd_syntax(config_path: str, verbose: bool = False) -> Tuple[bool, str]:
    """
    Validate dhcpd.conf syntax using dhcpd -t command.
    
    Args:
        config_path: Path to dhcpd.conf file
        verbose: If True, print detailed validation output
        
    Returns:
        Tuple of (is_valid, error_message)
        is_valid is True if syntax is correct, False otherwise
        error_message contains the error details if validation fails
    """
    try:
        # Try to find dhcpd binary
        dhcpd_paths = [
            '/usr/sbin/dhcpd',
            '/usr/local/sbin/dhcpd',
            '/opt/homebrew/sbin/dhcpd',
            'dhcpd'  # Fallback to PATH
        ]
        
        dhcpd_binary = None
        for path in dhcpd_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                dhcpd_binary = path
                break
        
        if not dhcpd_binary:
            # Try to find in PATH
            try:
                result = subprocess.run(
                    ['which', 'dhcpd'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    dhcpd_binary = result.stdout.strip()
            except:
                pass
        
        if not dhcpd_binary:
            # Cannot find dhcpd, skip validation with warning
            warning = "WARNING: dhcpd binary not found, skipping syntax validation"
            if verbose:
                print(warning)
            return True, warning
        
        if verbose:
            print(f"Using dhcpd binary: {dhcpd_binary}")
        
        # Run dhcpd -t to test configuration
        cmd = [dhcpd_binary, '-t', '-cf', config_path]
        
        if verbose:
            print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # dhcpd -t returns 0 on success
        if result.returncode == 0:
            if verbose:
                print("✓ dhcpd.conf syntax is valid")
            return True, ""
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            if verbose:
                print(f"✗ dhcpd.conf syntax validation failed:")
                print(error_msg)
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        error = "Timeout while validating dhcpd configuration"
        if verbose:
            print(f"ERROR: {error}")
        return False, error
    except Exception as e:
        error = f"Error validating dhcpd configuration: {e}"
        if verbose:
            print(f"ERROR: {error}")
        return False, error


def restore_from_backup(config_path: str, backup_path: str) -> bool:
    """Restore configuration from backup file."""
    try:
        shutil.copy2(backup_path, config_path)
        return True
    except Exception as e:
        print(f"ERROR: Failed to restore from backup: {e}")
        return False


def find_reservation_block(content: str, hostname_or_fqdn: str) -> Tuple[int, int]:
    """Find the start and end indices of a reservation block for the given host."""
    pattern = re.compile(rf"(^|\n)(host\s+{re.escape(hostname_or_fqdn)}\s*\{{[\s\S]*?\n\}})\n", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return -1, -1
    return match.start(2), match.end(0)


def find_reservation_by_mac(content: str, mac: str) -> Optional[Tuple[str, str, str]]:
    """Find a reservation block by MAC address."""
    norm_mac = normalize_mac(mac)
    if not norm_mac:
        return None
    
    pattern = re.compile(
        r"host\s+(\S+)\s*\{[^\}]*?hardware\s+ethernet\s+([0-9a-f:]+)\s*;[^\}]*?fixed-address\s+([\d.]+)\s*;[^\}]*?\}",
        re.MULTILINE | re.IGNORECASE | re.DOTALL
    )
    
    for match in pattern.finditer(content):
        found_hostname = match.group(1)
        found_mac = match.group(2).lower()
        found_ip = match.group(3)
        
        if found_mac == norm_mac:
            return (found_hostname, found_mac, found_ip)
    
    return None


def extract_all_reservations(content: str) -> List[Tuple[str, str, str]]:
    """Extract all DHCP reservations from dhcpd.conf content."""
    reservations: List[Tuple[str, str, str]] = []
    
    pattern = re.compile(
        r"host\s+(\S+)\s*\{[^\}]*?hardware\s+ethernet\s+([0-9a-f:]+)\s*;[^\}]*?fixed-address\s+([\d.]+)\s*;[^\}]*?\}",
        re.MULTILINE | re.IGNORECASE | re.DOTALL
    )
    
    for match in pattern.finditer(content):
        hostname = match.group(1)
        mac = match.group(2).lower()
        ip = match.group(3)
        reservations.append((hostname, mac, ip))
    
    return reservations


def write_csv(records: List[Tuple[str, str, str]], output_path: Optional[str], include_header: bool = True) -> None:
    """Write reservations to CSV file."""
    import sys
    
    output_file = open(output_path, 'w', newline='') if output_path else sys.stdout
    
    try:
        writer = csv.writer(output_file)
        
        if include_header:
            writer.writerow(['hostname', 'mac', 'ip'])
        
        for hostname, mac, ip in records:
            writer.writerow([hostname, mac, ip])
        
        if output_path:
            print(f"Exported {len(records)} reservation(s) to: {output_path}")
    finally:
        if output_path and output_file != sys.stdout:
            output_file.close()


def get_user_confirmation(prompt: str) -> bool:
    """Prompt user for yes/no confirmation."""
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


def add_reservation(content: str, hostname: str, mac: str, ip: str, domain: Optional[str], 
                   interactive: bool = True) -> Tuple[str, bool, Optional[str]]:
    """Add or update a DHCP reservation."""
    fqdn = f"{hostname}.{domain}" if domain and not hostname.endswith(f".{domain}") else hostname
    
    # Check if this MAC is already assigned
    existing = find_reservation_by_mac(content, mac)
    
    if existing:
        existing_hostname, existing_mac, existing_ip = existing
        
        # Check if this is an exact match (no change needed)
        if existing_hostname == fqdn and existing_ip == ip:
            print(f"Reservation for {fqdn} -> {mac} -> {ip} already exists, skipping")
            return content, False, None
        
        # Check if this is an update to the same host
        if existing_hostname == fqdn:
            print(f"Updating reservation for {fqdn}: {existing_ip} -> {ip}")
        else:
            # Conflict: MAC is assigned to a different hostname
            conflict_msg = f"MAC {mac} is already assigned to {existing_hostname} -> {existing_ip}"
            print(f"WARNING: {conflict_msg}")
            
            if interactive:
                prompt = (
                    f"Do you want to remove the old reservation ({existing_hostname} -> {existing_mac} -> {existing_ip}) "
                    f"and add the new one ({fqdn} -> {mac} -> {ip})?"
                )
                if not get_user_confirmation(prompt):
                    print(f"Skipping reservation: {fqdn} -> {mac} -> {ip}")
                    return content, False, "User declined to overwrite conflicting reservation"
                
                # Remove the old reservation first
                print(f"Removing conflicting reservation: {existing_hostname}")
                content, removed = remove_reservation(content, existing_hostname.split('.')[0], domain)
                if not removed:
                    return content, False, f"Failed to remove conflicting reservation for {existing_hostname}"
            else:
                error = f"Conflict: MAC {mac} is already used by {existing_hostname}. Run in interactive mode to resolve conflicts."
                print(f"ERROR: {error}")
                return content, False, error
    
    # Now add/update the reservation
    start, end = find_reservation_block(content, fqdn)
    block = build_reservation_block(hostname, mac, ip, domain)
    
    if start != -1:
        # Replace existing block
        prefix = ''
        if start > 0 and content[start-1] != '\n':
            prefix = '\n'
        
        new_content = content[:start] + prefix + block + content[end:]
        changed = (prefix + block) != content[start:end]
        return new_content, changed, None
    
    # Append with a separating newline if needed
    if content and not content.endswith('\n'):
        content += '\n'
    new_content = content + block
    return new_content, True, None


def remove_reservation(content: str, hostname: str, domain: Optional[str]) -> Tuple[str, bool]:
    fqdn = f"{hostname}.{domain}" if domain and not hostname.endswith(f".{domain}") else hostname
    start, end = find_reservation_block(content, fqdn)
    if start == -1:
        return content, False
    
    new_content = content[:start] + content[end:]
    return new_content, True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Manage DHCP reservations in dhcpd.conf (add/remove/export)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  Add a single reservation:
    %(prog)s --hostname server01 --mac 00:11:22:33:44:55 --ip 192.168.1.100 --action add

  Remove a single reservation:
    %(prog)s --hostname server01 --action remove

  Batch add from CSV:
    %(prog)s --file dhcp_hosts.csv --action add
    
  Run in non-interactive mode (skip prompts on conflicts):
    %(prog)s --file dhcp_hosts.csv --action add --non-interactive

  Export all reservations to CSV:
    %(prog)s --action export --output dhcp_backup.csv
    
  Export to stdout (no file):
    %(prog)s --action export
    
  Export without header row:
    %(prog)s --action export --output dhcp_backup.csv --no-header

CSV format (with or without header):
  hostname,mac,ip
  server01,00:11:22:33:44:55,192.168.1.100
  server02,00:11:22:33:44:56,192.168.1.101

Environment variables:
  DHCPD_CONF_PATH  Path to dhcpd.conf (default: ../ansible/roles/dhcpd/files/dhcpd.conf)
  DHCPD_DOMAIN     Domain appended to hostnames (default: macfarm.example.com)
        '''
    )

    parser.add_argument('--hostname', type=str, help='Hostname for the reservation')
    parser.add_argument('--mac', type=str, help='MAC address')
    parser.add_argument('--ip', type=str, help='IP address')
    parser.add_argument('--file', type=str, help='CSV file with hostname,mac,ip for batch operations')
    parser.add_argument('--action', type=str, required=True, choices=['add', 'remove', 'export'], help='Action to perform')
    parser.add_argument('--output', type=str, help='Output CSV file for export action')
    parser.add_argument('--no-header', action='store_true', help='Omit CSV header row in export output')
    parser.add_argument('--config-file', type=str, help='Path to dhcpd.conf file')
    parser.add_argument('--domain', type=str, help='Domain to append to hostnames')
    parser.add_argument('--no-backup', action='store_true', help='Disable automatic backup')
    parser.add_argument('--non-interactive', action='store_true', help='Run in non-interactive mode')
    parser.add_argument('--skip-validation', action='store_true', help='Skip dhcpd.conf syntax validation')
    parser.add_argument('--debug', action='store_true', help='Enable verbose output')
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Resolve config path
    config_path = (
        args.config_file
        or os.environ.get('DHCPD_CONF_PATH')
        or os.path.abspath(os.path.join(os.path.dirname(__file__), DEFAULT_RELATIVE_DHCPD_CONF))
    )

    if not os.path.isfile(config_path):
        print(f"ERROR: dhcpd.conf not found at: {config_path}")
        return 1

    domain = (
        args.domain
        or os.environ.get('DHCPD_DOMAIN')
        or 'macfarm.example.com'
    )

    # Handle export action separately
    if args.action == 'export':
        try:
            content = load_config_text(config_path)
            reservations = extract_all_reservations(content)
            
            if not reservations:
                print("No DHCP reservations found in dhcpd.conf")
                return 0
            
            if args.debug:
                print(f"Found {len(reservations)} reservation(s)")
            
            write_csv(reservations, args.output, include_header=not args.no_header)
            return 0
            
        except Exception as e:
            print(f"ERROR: export failed: {e}")
            return 1

    # Determine records to process
    records: List[Tuple[str, Optional[str], Optional[str]]] = []
    if args.file:
        try:
            batch = parse_csv(args.file)
            for hostname, mac, ip in batch:
                records.append((hostname, mac, ip))
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
    else:
        if args.action == 'add':
            if not args.hostname or not args.mac or not args.ip:
                print('ERROR: --hostname, --mac, and --ip are required for add when not using --file')
                return 1
            norm_mac = normalize_mac(args.mac or '')
            if not norm_mac:
                print(f"ERROR: invalid MAC address: {args.mac}")
                return 1
            if not validate_ip_address(args.ip or ''):
                print(f"ERROR: invalid IP address: {args.ip}")
                return 1
            records.append((args.hostname.strip(), norm_mac, args.ip.strip()))
        else:  # remove
            if not args.hostname:
                print('ERROR: --hostname is required for remove when not using --file')
                return 1
            records.append((args.hostname.strip(), None, None))

    # Load config
    try:
        content = load_config_text(config_path)
    except Exception as e:
        print(f"ERROR: failed reading config: {e}")
        return 1

    # Validate syntax before making changes
    if not args.skip_validation:
        if args.debug:
            print("Validating current dhcpd.conf syntax...")
        is_valid, error_msg = validate_dhcpd_syntax(config_path, verbose=args.debug)
        if not is_valid:
            print(f"ERROR: Current dhcpd.conf has syntax errors:")
            print(error_msg)
            print("\nPlease fix the syntax errors before using this script.")
            return 1

    # Create backup
    backup_path = None
    if not args.no_backup:
        try:
            backup_path = make_backup(config_path)
            if args.debug:
                print(f"Backup created: {backup_path}")
        except Exception as e:
            print(f"ERROR: failed to create backup: {e}")
            return 1

    total = len(records)
    ok = 0
    fail = 0
    
    interactive_mode = not args.non_interactive
    
    if args.debug:
        print(f"Processing {total} record(s)...")

    for (hostname, mac, ip) in records:
        try:
            if args.action == 'add':
                new_content, changed, error = add_reservation(
                    content, hostname, mac or '', ip or '', domain, interactive=interactive_mode
                )
                if error:
                    print(f"ERROR: {hostname}: {error}")
                    fail += 1
                    continue
            else:
                new_content, changed = remove_reservation(content, hostname, domain)
                
            if changed:
                content = new_content
                ok += 1
            else:
                if args.debug:
                    print(f"No change needed for host: {hostname}")
                ok += 1
        except Exception as e:
            print(f"ERROR: failed processing host {hostname}: {e}")
            fail += 1

    # Save the updated configuration
    try:
        save_config_text(config_path, content)
    except Exception as e:
        print(f"ERROR: failed writing config: {e}")
        return 1

    # Validate syntax after making changes
    if not args.skip_validation:
        if args.debug:
            print("\nValidating updated dhcpd.conf syntax...")
        is_valid, error_msg = validate_dhcpd_syntax(config_path, verbose=args.debug)
        
        if not is_valid:
            print(f"\n{'='*60}")
            print("ERROR: Updated dhcpd.conf has syntax errors!")
            print(f"{'='*60}")
            print(error_msg)
            
            if backup_path and os.path.isfile(backup_path):
                print(f"\nRestoring from backup: {backup_path}")
                if restore_from_backup(config_path, backup_path):
                    print("✓ Configuration restored from backup")
                else:
                    print("✗ Failed to restore from backup!")
            
            return 1
        else:
            if args.debug:
                print("✓ Updated dhcpd.conf syntax is valid")

    print(f"\nSummary: {ok} successful, {fail} failed, total {total}")
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

