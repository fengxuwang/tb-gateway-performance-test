"""
BACnet CLI subcommand.
"""

import argparse
import asyncio
import logging
import sys

from simulators.bacnet import BACnetSimulator, distribute_objects
from simulators.utils import get_local_ipv4
from .base import add_common_arguments, setup_logging, run_simulation_loop

log = logging.getLogger("bacnet-simulator")


def create_bacnet_parser():
    """Create argument parser for BACnet subcommand."""
    parser = argparse.ArgumentParser(
        description="BACnet Simulator for ThingsBoard Gateway Performance Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulate 5 devices, 50 objects each
  python main.py bacnet --devices 5 --objects-per-device 50

  # Simulate 10 devices with specific port range
  python main.py bacnet --devices 10 --objects-per-device 100 --base-port 47810

  # Custom object distribution
  python main.py bacnet --devices 3 --analog-inputs 20 --binary-inputs 10 --analog-values 15

  # Generate gateway config only
  python main.py bacnet --devices 5 --objects-per-device 30 --generate-config-only
        """,
    )

    # Add common arguments
    add_common_arguments(parser)

    # BACnet-specific arguments
    parser.add_argument(
        "--base-port", type=int, default=47809,
        help="模拟设备的 UDP 端口起始值 (默认: 47809，Gateway 使用 47808)",
    )
    parser.add_argument(
        "--base-device-id", type=int, default=100,
        help="BACnet 设备 ID 起始值 (默认: 100)",
    )

    # BACnet object type arguments
    parser.add_argument(
        "--analog-inputs", type=int, default=None,
        help="模拟输入对象数量"
    )
    parser.add_argument(
        "--analog-outputs", type=int, default=None,
        help="模拟输出对象数量"
    )
    parser.add_argument(
        "--analog-values", type=int, default=None,
        help="模拟值对象数量"
    )
    parser.add_argument(
        "--binary-inputs", type=int, default=None,
        help="二进制输入对象数量"
    )
    parser.add_argument(
        "--binary-outputs", type=int, default=None,
        help="二进制输出对象数量"
    )
    parser.add_argument(
        "--binary-values", type=int, default=None,
        help="二进制值对象数量"
    )
    parser.add_argument(
        "--multistate-inputs", type=int, default=None,
        help="多状态输入对象数量"
    )
    parser.add_argument(
        "--multistate-outputs", type=int, default=None,
        help="多状态输出对象数量"
    )
    parser.add_argument(
        "--multistate-values", type=int, default=None,
        help="多状态值对象数量"
    )

    return parser


async def run_bacnet(argv=None):
    """Run BACnet simulator with given arguments.

    Args:
        argv: Command line arguments (excluding program name and subcommand)
    """
    parser = create_bacnet_parser()
    args = parser.parse_args(argv)

    # Set up logging
    setup_logging(args.log_level)

    # Build per-type distribution if any overrides given
    has_overrides = any([
        args.analog_inputs, args.analog_outputs, args.analog_values,
        args.binary_inputs, args.binary_outputs, args.binary_values,
        args.multistate_inputs, args.multistate_outputs, args.multistate_values,
    ])

    distribution = None
    if has_overrides:
        distribution = {
            "analog_input": args.analog_inputs or 0,
            "analog_output": args.analog_outputs or 0,
            "analog_value": args.analog_values or 0,
            "binary_input": args.binary_inputs or 0,
            "binary_output": args.binary_outputs or 0,
            "binary_value": args.binary_values or 0,
            "multistate_input": args.multistate_inputs or 0,
            "multistate_output": args.multistate_outputs or 0,
            "multistate_value": args.multistate_values or 0,
        }
        total = sum(distribution.values())
        if total == 0:
            log.error("All object counts are 0, nothing to simulate")
            sys.exit(1)

    device_configs = []

    log.info("=" * 60)
    log.info("BACnet Simulator for ThingsBoard Gateway")
    log.info("=" * 60)
    log.info(f"Connectors: {args.connectors}")
    log.info(f"Devices per connector: {args.devices}")
    log.info(f"Objects per device: {args.objects_per_device}")
    log.info(f"Base port: {args.base_port}")
    log.info(f"Update interval: {args.update_interval}s")
    log.info("=" * 60)

    # Create device configs for all connectors
    total_devices = args.connectors * args.devices
    for i in range(total_devices):
        device_id = args.base_device_id + i
        port = args.base_port + i
        obj_count = args.objects_per_device

        cfg = BACnetSimulator.create_device_config(
            device_id=device_id,
            port=port,
            object_count=obj_count,
            distribution=distribution,
            poll_period=args.poll_period,
            host=args.gateway_host,
            ip=args.ip,
        )
        device_configs.append(cfg)

        connector_num = i // args.devices + 1
        device_num_in_connector = i % args.devices + 1

        log.info(
            f"Device {device_id} (port {port}) [Connector {connector_num}, Device {device_num_in_connector}]: "
            f"AI={cfg.analog_input_count} AO={cfg.analog_output_count} "
            f"AV={cfg.analog_value_count} BI={cfg.binary_input_count} "
            f"BO={cfg.binary_output_count} BV={cfg.binary_value_count} "
            f"MSI={cfg.multistate_input_count} MSO={cfg.multistate_output_count} "
            f"MSV={cfg.multistate_value_count} "
            f"(total={obj_count})"
        )

    # Run simulation
    await run_simulation_loop(BACnetSimulator, device_configs, args)


def main_bacnet():
    """Entry point for BACnet subcommand."""
    asyncio.run(run_bacnet())
