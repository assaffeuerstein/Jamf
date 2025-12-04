# Example Files

This directory contains example configuration and data files.

## CSV Files

### hosts.csv

Standard CSV format for Mac provisioning operations. Contains hostname, MAC address, and IP address.

```csv
hostname,mac,ip
build-mac-01,00:11:22:33:44:01,10.0.0.101
```

Use with:
- `mac_provisioning_manager.py --file hosts.csv --domain macfarm.example.com`
- Jenkins pipeline "Add/Remove Mac"
- Web interface file upload

### hosts_with_serial.csv

Alternative format with serial numbers and locations. Useful for inventory management.

```csv
hostname,serial_number,location
build-mac-01,C02XXXXX001,Rack A-01
```

## Usage

1. Copy the example file and modify it with your actual data
2. Remove the header row if your tooling requires it (most scripts auto-detect headers)
3. Ensure MAC addresses are in the correct format (XX:XX:XX:XX:XX:XX)
4. Verify IP addresses are within your allowed ranges

