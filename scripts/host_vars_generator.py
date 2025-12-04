#!/usr/bin/env python3
"""
Host Vars Generator

Generates minimal Ansible host_vars files containing:
- static_ip
- my_hostname (FQDN)
- my_shortname

Supports single record via CLI params or batch via CSV.
Output path: ../ansible/host_vars/<fqdn>.yml

Features:
- Conflict detection for hostnames and IP addresses
- Interactive confirmation for overwrites
- Automatic cleanup of conflicting files
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import shared CSV parsing utility
from csv_utils import parse_mac_ip_csv


DEFAULT_HOST_VARS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ansible', 'host_vars'))


def validate_ip(ip: str) -> bool:
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except (ValueError, TypeError):
        return False


def fqdn_to_shortname(fqdn: str) -> str:
    return fqdn.split('.')[0]


def ensure_host_vars_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def parse_host_vars_file(file_path: str) -> Dict[str, str]:
    """Parse a host_vars YAML file to extract hostname and IP."""
    data = {}
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Extract my_hostname
            hostname_match = re.search(r'^my_hostname:\s*(.+)$', content, re.MULTILINE)
            if hostname_match:
                data['hostname'] = hostname_match.group(1).strip()
            
            # Extract static_ip
            ip_match = re.search(r'^static_ip:\s*(.+)$', content, re.MULTILINE)
            if ip_match:
                data['ip'] = ip_match.group(1).strip()
    except Exception as e:
        print(f"WARNING: Failed to parse {file_path}: {e}")
    
    return data


def scan_host_vars_directory(dir_path: str) -> Dict[str, Dict[str, str]]:
    """Scan all YAML files in host_vars directory."""
    results = {}
    
    if not os.path.isdir(dir_path):
        return results
    
    for filename in os.listdir(dir_path):
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path):
                data = parse_host_vars_file(file_path)
                if data:
                    results[filename] = data
    
    return results


def find_conflicts(dir_path: str, fqdn: str, ip: str) -> Tuple[Optional[str], Optional[str]]:
    """Check if hostname or IP already exists in any host_vars file."""
    existing_files = scan_host_vars_directory(dir_path)
    expected_filename = f"{fqdn}.yml"
    
    hostname_conflict = None
    ip_conflict = None
    
    for filename, data in existing_files.items():
        # Check for hostname conflict
        if data.get('hostname') == fqdn and filename != expected_filename:
            hostname_conflict = filename
        
        # Check for IP conflict
        if data.get('ip') == ip:
            if filename != expected_filename or data.get('hostname') != fqdn:
                ip_conflict = filename
    
    return hostname_conflict, ip_conflict


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


def write_host_vars_file(dir_path: str, fqdn: str, ip: str, interactive: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """Write a host_vars YAML file with conflict detection."""
    short = fqdn_to_shortname(fqdn)
    expected_path = os.path.join(dir_path, f"{fqdn}.yml")
    
    # Check for conflicts
    hostname_conflict, ip_conflict = find_conflicts(dir_path, fqdn, ip)
    
    # Check if the exact file already exists with the same content
    if os.path.exists(expected_path):
        existing_data = parse_host_vars_file(expected_path)
        if existing_data.get('hostname') == fqdn and existing_data.get('ip') == ip:
            print(f"Host vars for {fqdn} -> {ip} already exists, skipping")
            return expected_path, None
    
    # Handle conflicts
    files_to_delete = set()
    
    if hostname_conflict or ip_conflict:
        conflict_files = set()
        if hostname_conflict:
            conflict_files.add(hostname_conflict)
        if ip_conflict:
            conflict_files.add(ip_conflict)
        
        # Build conflict message
        conflict_msg_parts = []
        if hostname_conflict:
            conflict_msg_parts.append(f"hostname '{fqdn}' exists in {hostname_conflict}")
        if ip_conflict:
            conflict_msg_parts.append(f"IP '{ip}' exists in {ip_conflict}")
        
        conflict_msg = " and ".join(conflict_msg_parts)
        print(f"WARNING: Conflict detected - {conflict_msg}")
        
        if interactive:
            for conf_file in conflict_files:
                conf_path = os.path.join(dir_path, conf_file)
                conf_data = parse_host_vars_file(conf_path)
                print(f"  Conflicting file: {conf_file}")
                print(f"    hostname: {conf_data.get('hostname', 'N/A')}")
                print(f"    IP: {conf_data.get('ip', 'N/A')}")
            
            prompt = f"Do you want to delete the conflicting file(s) and create {fqdn}.yml with {ip}?"
            if not get_user_confirmation(prompt):
                print(f"Skipping: {fqdn} -> {ip}")
                return None, "User declined to overwrite conflicting file(s)"
            
            files_to_delete = conflict_files
        else:
            error = f"Conflict: {conflict_msg}. Run in interactive mode to resolve conflicts."
            print(f"ERROR: {error}")
            return None, error
    
    # Delete conflicting files if user approved
    for conf_file in files_to_delete:
        conf_path = os.path.join(dir_path, conf_file)
        try:
            os.remove(conf_path)
            print(f"Deleted conflicting file: {conf_file}")
        except Exception as e:
            error = f"Failed to delete {conf_file}: {e}"
            print(f"ERROR: {error}")
            return None, error
    
    # Write the new file
    content = (
        f"my_hostname: {fqdn}\n"
        f"my_shortname: {short}\n"
        f"static_ip: {ip}\n"
    )
    
    try:
        with open(expected_path, 'w') as f:
            f.write(content)
        return expected_path, None
    except Exception as e:
        error = f"Failed to write file: {e}"
        print(f"ERROR: {error}")
        return None, error


def parse_csv(file_path: str) -> List[Tuple[str, str]]:
    """Parse CSV file and extract hostname (FQDN) and IP address."""
    full_records = parse_mac_ip_csv(
        file_path=file_path,
        mac_validator=None,
        ip_validator=validate_ip
    )
    
    return [(hostname, ip) for hostname, _mac, ip in full_records]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate Ansible host_vars files (static_ip, my_hostname, my_shortname)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  Single host:
    %(prog)s --hostname build-mac-01.macfarm.example.com --ip 10.0.0.100

  Batch from CSV:
    %(prog)s --file hosts.csv
    
  Non-interactive mode (skip prompts on conflicts):
    %(prog)s --file hosts.csv --non-interactive

CSV format (unified; header optional):
  hostname,mac,ip
  build-mac-01.macfarm.example.com,00:11:22:33:44:55,10.0.0.100
  build-mac-02.macfarm.example.com,00:11:22:33:44:56,10.0.0.101
        '''
    )

    parser.add_argument('--hostname', type=str, help='FQDN hostname')
    parser.add_argument('--ip', type=str, help='Static IP')
    parser.add_argument('--file', type=str, help='CSV file with hostname,mac,ip for batch mode')
    parser.add_argument('--out-dir', type=str, help=f'Output directory (default: {DEFAULT_HOST_VARS_DIR})')
    parser.add_argument('--non-interactive', action='store_true', help='Run in non-interactive mode')
    parser.add_argument('--debug', action='store_true', help='Enable verbose output')
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    out_dir = args.out_dir or DEFAULT_HOST_VARS_DIR
    ensure_host_vars_dir(out_dir)

    records: List[Tuple[str, str]] = []
    if args.file:
        try:
            records = parse_csv(args.file)
        except Exception as e:
            print(f"ERROR: {e}")
            return 1
    else:
        if not args.hostname or not args.ip:
            print('ERROR: --hostname and --ip are required when not using --file')
            return 1
        if not validate_ip(args.ip):
            print(f"ERROR: invalid IP: {args.ip}")
            return 1
        records = [(args.hostname.strip(), args.ip.strip())]

    ok = 0
    fail = 0
    
    interactive_mode = not args.non_interactive
    
    if args.debug:
        print(f"Processing {len(records)} record(s)...")
    
    for fqdn, ip in records:
        try:
            out_path, error = write_host_vars_file(out_dir, fqdn, ip, interactive=interactive_mode)
            
            if error:
                print(f"ERROR: {fqdn}: {error}")
                fail += 1
                continue
            
            if out_path:
                if args.debug:
                    print(f"Wrote: {out_path}")
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"ERROR: failed writing {fqdn}: {e}")
            fail += 1

    print(f"Summary: {ok} successful, {fail} failed, total {ok + fail}")
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

