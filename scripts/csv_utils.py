#!/usr/bin/env python3
"""
CSV Parsing Utilities

Shared CSV parsing functions with robust header detection that works
correctly with single-line CSV files and various formats.
"""

import csv
import re
from typing import List, Tuple, Optional, Callable


def is_mac_address(value: str) -> bool:
    """Check if value looks like a MAC address."""
    mac_pattern = r'^[0-9a-fA-F]{2}([:-])[0-9a-fA-F]{2}(\1[0-9a-fA-F]{2}){4}$'
    return bool(re.match(mac_pattern, value))


def is_ip_address(value: str) -> bool:
    """Check if value looks like an IPv4 address."""
    parts = value.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except (ValueError, TypeError):
        return False


def parse_csv_with_smart_header_detection(
    file_path: str,
    expected_columns: int,
    validator: Optional[Callable[[List[str]], bool]] = None,
    column_names: Optional[List[str]] = None
) -> Tuple[List[List[str]], bool]:
    """
    Parse CSV file with smart header detection that works with single-line files.
    
    This function fixes the bug where csv.Sniffer() incorrectly identifies the only
    data line as a header in single-line CSV files.
    
    Args:
        file_path: Path to CSV file
        expected_columns: Minimum expected number of columns
        validator: Optional function that returns True if a row looks like data
        column_names: Optional list of expected column header names
        
    Returns:
        Tuple of (records, has_header) where records is list of row lists
        
    Raises:
        ValueError: If file is empty or has no valid records
    """
    with open(file_path, 'r') as f:
        # Read the first line to check if it's a header
        first_line = f.readline().strip()
        if not first_line:
            raise ValueError("CSV file is empty")
        
        f.seek(0)
        
        # Determine if there's a header
        has_header = False
        
        try:
            # Parse the first line
            first_row = next(csv.reader([first_line]))
            
            if len(first_row) >= expected_columns:
                # Check if validator says this looks like data
                if validator and validator(first_row):
                    has_header = False
                # Check if column names match expected header keywords
                elif column_names:
                    first_row_lower = [col.lower().strip() for col in first_row]
                    has_header = any(name.lower() in first_row_lower for name in column_names)
                else:
                    # Fall back to CSV Sniffer for multi-line files
                    sample = f.read(1024)
                    f.seek(0)
                    try:
                        has_header = csv.Sniffer().has_header(sample)
                    except Exception:
                        # If sniffer fails, assume no header
                        has_header = False
        except Exception:
            # If parsing fails, assume no header
            has_header = False
        
        # Read all records
        reader = csv.reader(f)
        if has_header:
            next(reader, None)
        
        records = []
        for row in reader:
            # Skip empty lines
            if not row or all(not cell.strip() for cell in row):
                continue
            records.append(row)
    
    if not records:
        raise ValueError("No valid records found in CSV file")
    
    return records, has_header


def parse_mac_ip_csv(
    file_path: str,
    mac_validator: Optional[Callable[[str], Optional[str]]] = None,
    ip_validator: Optional[Callable[[str], bool]] = None
) -> List[Tuple[str, str, str]]:
    """
    Parse CSV file with format: hostname, mac, ip.
    
    Uses smart header detection that works correctly with single-line CSV files.
    
    Args:
        file_path: Path to CSV file
        mac_validator: Optional function to normalize/validate MAC addresses
        ip_validator: Optional function to validate IP addresses
        
    Returns:
        List of tuples (hostname, mac, ip)
        
    Raises:
        ValueError: If no valid records found
    """
    def looks_like_data(row: List[str]) -> bool:
        """Check if row looks like data (has MAC and IP patterns)."""
        if len(row) < 3:
            return False
        return is_mac_address(row[1].strip()) and is_ip_address(row[2].strip())
    
    raw_records, _ = parse_csv_with_smart_header_detection(
        file_path=file_path,
        expected_columns=3,
        validator=looks_like_data,
        column_names=['hostname', 'mac', 'ip', 'address']
    )
    
    # Process and validate records
    validated_records = []
    for idx, row in enumerate(raw_records, start=1):
        if len(row) < 3:
            print(f"WARNING: CSV line {idx}: expected 'hostname,mac,ip' - skipping")
            continue
        
        hostname = row[0].strip()
        mac = row[1].strip()
        ip = row[2].strip()
        
        # Validate MAC address
        if mac_validator:
            mac = mac_validator(mac)
            if not mac:
                print(f"WARNING: CSV line {idx}: invalid MAC address - skipping")
                continue
        
        # Validate IP address
        if ip_validator and not ip_validator(ip):
            print(f"WARNING: CSV line {idx}: invalid IP address - skipping")
            continue
        
        if not hostname:
            print(f"WARNING: CSV line {idx}: empty hostname - skipping")
            continue
        
        validated_records.append((hostname, mac, ip))
    
    if not validated_records:
        raise ValueError("No valid records found in CSV file")
    
    return validated_records


def parse_hostname_serial_csv(file_path: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    Parse CSV file with format: hostname, serial_number, [location].
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of tuples (hostname, serial_number, location)
        
    Raises:
        ValueError: If no valid records found
    """
    raw_records, _ = parse_csv_with_smart_header_detection(
        file_path=file_path,
        expected_columns=2,
        column_names=['hostname', 'host', 'serial', 'location']
    )
    
    validated_records = []
    for idx, row in enumerate(raw_records, start=1):
        if len(row) < 2:
            print(f"WARNING: CSV line {idx}: expected at least 'hostname,serial' - skipping")
            continue
        
        hostname = row[0].strip()
        serial_number = row[1].strip()
        location = row[2].strip() if len(row) >= 3 else None
        
        if not hostname or not serial_number:
            print(f"WARNING: CSV line {idx}: empty hostname or serial number - skipping")
            continue
        
        validated_records.append((hostname, serial_number, location))
    
    if not validated_records:
        raise ValueError("No valid records found in CSV file")
    
    return validated_records

