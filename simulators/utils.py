"""
Utility functions for protocol simulators.
"""

import platform
import re
import socket
import subprocess


def get_local_ipv4():
    """Get the local IPv4 address of the machine.

    Prioritizes LAN IP ranges (192.168.x.x, 10.x.x.x, 172.16-31.x.x) over VPN/other interfaces.
    """
    # Priority order for IP ranges
    priority_ranges = [
        '192.168.',  # Most common private network
        '10.',       # Class A private network
        '172.16.', '172.17.', '172.18.', '172.19.',
        '172.20.', '172.21.', '172.22.', '172.23.',
        '172.24.', '172.25.', '172.26.', '172.27.',
        '172.28.', '172.29.', '172.30.', '172.31.',
    ]

    all_ips = []

    try:
        system = platform.system().lower()

        if system == 'darwin':  # macOS
            # Use ifconfig on macOS
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            output = result.stdout
            # Find all IPv4 addresses (excluding 127.0.0.1)
            ips = re.findall(r'inet\s+(\d+\.\d+\.\d+\.\d+)', output)
            all_ips = [ip for ip in ips if not ip.startswith('127.')]

        elif system == 'linux':
            # Use ip command on Linux
            result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
            output = result.stdout
            ips = re.findall(r'inet\s+(\d+\.\d+\.\d+\.\d+)', output)
            all_ips = [ip for ip in ips if not ip.startswith('127.')]

        elif system == 'windows':
            # Use ipconfig on Windows
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            output = result.stdout
            ips = re.findall(r'IPv4.*?:\s*(\d+\.\d+\.\d+\.\d+)', output)
            all_ips = [ip for ip in ips if not ip.startswith('127.')]

    except Exception:
        pass

    # Sort by priority
    for prefix in priority_ranges:
        for ip in all_ips:
            if ip.startswith(prefix):
                return ip

    # If no priority IP found, try socket method
    if all_ips:
        return all_ips[0]

    # Final fallback: use socket connection method
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Connect to a public DNS server (doesn't actually send data)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]

            # If it's a VPN-like IP (not in private ranges), try alternative
            if not (local_ip.startswith('192.168.') or local_ip.startswith('10.') or
                    local_ip.startswith('172.') or local_ip.startswith('127.')):
                # Try connecting to local gateway instead
                try:
                    s.connect(("192.168.1.1", 80))
                    local_ip = s.getsockname()[0]
                except Exception:
                    pass

            return local_ip
    except Exception:
        # Final fallback
        return "127.0.0.1"


async def handle_config_only_mode(gateway_config: dict, protocol: str, args) -> None:
    """Handle config-only mode: save files and print summary, then exit.

    Args:
        gateway_config: Gateway configuration (single or multiple connectors)
        protocol: Protocol name (e.g., 'bacnet', 'modbus')
        args: Command line arguments (must have 'connectors' and 'config_dir' attributes)
    """
    import json
    import logging
    import os

    log = logging.getLogger(f"{protocol}-simulator")

    # Get config directory from args
    config_dir = getattr(args, 'config_dir', 'config')

    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    # Handle both single and multiple connectors with the same file structure
    if args.connectors == 1:
        # Single connector - convert to list format for consistent handling
        connector_config = gateway_config
        connector_configs = [connector_config]
        connector_count = 1
    else:
        # Multiple connectors
        connector_configs = gateway_config['connectors']
        connector_count = gateway_config['count']

    # Generate separate config files for each connector
    for idx, connector_config in enumerate(connector_configs):
        connector_filename = f"{protocol}_{idx + 1}.json"
        connector_path = os.path.join(config_dir, connector_filename)
        with open(connector_path, "w") as f:
            json.dump(connector_config, f, indent=2)
        log.info(f"Connector {idx + 1} config written to {connector_path}")

    # Write complete tb_gateway.json with proper structure
    connectors_list = []
    for idx in range(connector_count):
        # Reference files with just the filename (for Gateway to find in same directory)
        connector_filename = f"{protocol}_{idx + 1}.json"
        connectors_list.append({
            "name": f"{protocol.upper()}-Connector-{idx + 1}",
            "type": protocol,
            "configuration": connector_filename
        })

    tb_gateway_config = {
        "thingsboard": {
            "host": "localhost",
            "port": 1883,
            "remoteShell": False,
            "remoteConfiguration": False,
            "security": {
                "type": "basic",
                "username": "YOUR_USERNAME",
                "password": "YOUR_PASSWORD"
            }
        },
        "storage": {
            "type": "memory",
            "read_records_count": 100,
            "max_records_count": 100000,
            "data_folder_path": "./data/"
        },
        "connectors": connectors_list
    }

    tb_gateway_path = os.path.join(config_dir, "tb_gateway.json")
    with open(tb_gateway_path, "w") as f:
        json.dump(tb_gateway_config, f, indent=2)
    log.info(f"Gateway config written to {tb_gateway_path}")

    # Print summary
    print("\n" + "=" * 60)
    print(f"生成了 {connector_count} 个连接器配置文件")
    print("=" * 60)
    print(f"\n配置目录: {config_dir}/")
    print("\n生成的文件：")
    print(f"  - {config_dir}/tb_gateway.json  (Gateway 主配置文件)")
    for idx in range(connector_count):
        print(f"  - {config_dir}/{protocol}_{idx + 1}.json  (连接器 {idx + 1} 配置)")
    print("\n连接器详情：")
    for idx, connector_config in enumerate(connector_configs):
        print(f"\n连接器 {idx + 1}:")
        print(f"  文件: {config_dir}/{protocol}_{idx + 1}.json")
        print(f"  名称: {protocol.upper()}-Connector-{idx + 1}")
        print(f"  端口: {connector_config['application']['port']}")
        print(f"  设备数量: {len(connector_config['devices'])}")
        for device in connector_config['devices']:
            print(f"    - {device['host']}:{device['port']}")


async def save_gateway_configs(gateway_config, protocol: str, args):
    """Save gateway configuration files.

    Args:
        gateway_config: Gateway configuration (single or multiple connectors)
        protocol: Protocol name (e.g., 'bacnet', 'modbus')
        args: Command line arguments (must have 'connectors' and 'config_dir' attributes)

    Returns:
        Path to the main gateway config file
    """
    import json
    import logging
    import os

    log = logging.getLogger(f"{protocol}-simulator")

    # Get config directory from args
    config_dir = getattr(args, 'config_dir', 'config')

    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)

    # Handle both single and multiple connectors
    if args.connectors == 1:
        connector_configs = [gateway_config]
        connector_count = 1
    else:
        connector_configs = gateway_config['connectors']
        connector_count = gateway_config['count']

    # Generate separate config files for each connector
    for idx, connector_config in enumerate(connector_configs):
        connector_filename = f"{protocol}_{idx + 1}.json"
        connector_path = os.path.join(config_dir, connector_filename)
        with open(connector_path, "w") as f:
            json.dump(connector_config, f, indent=2)
        log.info(f"Connector {idx + 1} config written to {connector_path}")

    # Write complete tb_gateway.json with proper structure
    connectors_list = []
    for idx in range(connector_count):
        # Reference files with just the filename (for Gateway to find in same directory)
        connector_filename = f"{protocol}_{idx + 1}.json"
        connectors_list.append({
            "name": f"{protocol.upper()}-Connector-{idx + 1}",
            "type": protocol,
            "configuration": connector_filename
        })

    tb_gateway_config = {
        "thingsboard": {
            "host": "localhost",
            "port": 1883,
            "remoteShell": False,
            "remoteConfiguration": False,
            "security": {
                "type": "basic",
                "username": "YOUR_USERNAME",
                "password": "YOUR_PASSWORD"
            }
        },
        "storage": {
            "type": "memory",
            "read_records_count": 100,
            "max_records_count": 100000,
            "data_folder_path": "./data/"
        },
        "connectors": connectors_list
    }

    tb_gateway_path = os.path.join(config_dir, "tb_gateway.json")
    with open(tb_gateway_path, "w") as f:
        json.dump(tb_gateway_config, f, indent=2)
    log.info(f"Gateway config written to {tb_gateway_path}")

    return tb_gateway_path
