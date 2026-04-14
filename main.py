#!/usr/bin/env python3
"""
Protocol Simulators for ThingsBoard Gateway Performance Testing.

Supports multiple protocols (BACnet, Modbus, etc.) with a unified CLI.

Usage:
    python main.py bacnet --devices 5 --objects-per-device 50
    python main.py modbus --devices 10 --holding-registers 100
    python main.py --help

For backward compatibility (BACnet only):
    python main.py --devices 5  # Automatically treats as BACnet command
"""

import sys
from cli import AVAILABLE_PROTOCOLS


def show_help():
    """Show main help message."""
    print("Protocol Simulators for ThingsBoard Gateway Performance Testing")
    print()
    print("Usage: python main.py <protocol> [options]")
    print()
    print("Available protocols:")
    for protocol in AVAILABLE_PROTOCOLS:
        print(f"  {protocol}")
    print()
    print("Examples:")
    print("  python main.py bacnet --devices 5 --objects-per-device 50")
    print("  python main.py bacnet --help  # Show protocol-specific help")
    print()
    print("For backward compatibility (BACnet only):")
    print("  python main.py --devices 5  # Automatically treats as BACnet")


def is_known_option(arg):
    """Check if an argument is a known option (starts with -)."""
    return arg.startswith("-")


def main():
    """Main entry point - dispatches to protocol-specific subcommands."""
    # Handle help or no arguments
    if len(sys.argv) < 2:
        show_help()
        return

    first_arg = sys.argv[1]

    # Handle help flags
    if first_arg in ["--help", "-h", "help"]:
        show_help()
        return

    # Check if first arg is a known protocol
    if first_arg in AVAILABLE_PROTOCOLS:
        protocol = first_arg
        # Pass remaining arguments to protocol subcommand
        argv = sys.argv[2:]

        if protocol == "bacnet":
            from cli.bacnet import run_bacnet
            import asyncio
            asyncio.run(run_bacnet(argv))
        elif protocol == "modbus":
            from cli.modbus import run_modbus
            import asyncio
            asyncio.run(run_modbus(argv))
        else:
            print(f"Protocol '{protocol}' not yet implemented")
            sys.exit(1)
    else:
        # Backward compatibility: if first arg is not a known protocol,
        # assume it's a BACnet option and prepend "bacnet"
        argv = sys.argv[1:]  # Skip program name
        from cli.bacnet import run_bacnet
        import asyncio
        asyncio.run(run_bacnet(argv))


if __name__ == "__main__":
    main()
