#!/usr/bin/env python3
"""
BACnet Simulator for ThingsBoard Gateway Performance Testing.

Simulates multiple BACnet devices, each with configurable numbers of
analog/binary/multistate objects. Compatible with the ThingsBoard Gateway
BACnet connector (bacpypes3-based).

Usage:
    python main.py --devices 5 --objects-per-device 20 --base-port 47809

    python main.py --devices 5 --objects-per-device 50

    python main.py --devices 3 --analog-inputs 30 --binary-inputs 10 --analog-values 20

    python main.py --devices 5 --objects-per-device 30 --generate-config-only

    python main.py --devices 10 --objects-per-device 100 --base-port 47809 --update-interval 3
"""

import argparse
import asyncio
import logging
import signal
import sys

# Import BACnet simulator module and utilities
from simulators.bacnet import (
    BACnetSimulator,
    BACnetDeviceConfig,
    BACnetSimulatedDevice,
    distribute_objects,
)
from simulators.utils import (
    get_local_ipv4,
    handle_config_only_mode,
    save_gateway_configs,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bacnet-simulator")


# ---------- Command Line Arguments ----------

def parse_args():
    parser = argparse.ArgumentParser(
        description="BACnet Simulator for ThingsBoard Gateway Performance Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simulate 5 devices, 50 objects each
  python main.py --devices 5 --objects-per-device 50

  # Simulate 10 devices with specific port range
  python main.py --devices 10 --objects-per-device 100 --base-port 47810

  # Custom object distribution
  python main.py --devices 3 --analog-inputs 20 --binary-inputs 10 --analog-values 15

  # Generate gateway config only
  python main.py --devices 5 --objects-per-device 30 --generate-config-only
        """,
    )
    parser.add_argument(
        "--devices", type=int, default=1,
        help="每个连接器的 BACnet 设备数量 (默认: 1)",
    )
    parser.add_argument(
        "--connectors", type=int, default=1,
        help="生成的连接器配置文件数量，每个连接器独立配置指定数量的设备 (默认: 1)",
    )
    parser.add_argument(
        "--objects-per-device", type=int, default=10,
        help="每个设备的 BACnet 对象数量 (默认: 10)",
    )
    parser.add_argument(
        "--base-port", type=int, default=47809,
        help="模拟设备的 UDP 端口起始值 (默认: 47809，Gateway 使用 47808)",
    )
    parser.add_argument(
        "--base-device-id", type=int, default=100,
        help="BACnet 设备 ID 起始值 (默认: 100)",
    )
    parser.add_argument(
        "--update-interval", type=float, default=5.0,
        help="数据更新间隔，单位秒 (默认: 5.0)",
    )
    parser.add_argument(
        "--ip", type=str, default=get_local_ipv4(),
        help=f"模拟器绑定的 IP 地址 (默认: {get_local_ipv4()}，自动检测)",
    )
    parser.add_argument(
        "--gateway-host", type=str, default=None,
        help="Gateway 连接的主机地址 (默认: 使用 --ip 的值)",
    )
    parser.add_argument(
        "--poll-period", type=int, default=5000,
        help="Gateway 轮询设备的周期，单位毫秒 (默认: 5000)",
    )

    # 对象类型数量覆盖参数
    parser.add_argument("--analog-inputs", type=int, default=None, help="模拟输入对象数量")
    parser.add_argument("--analog-outputs", type=int, default=None, help="模拟输出对象数量")
    parser.add_argument("--analog-values", type=int, default=None, help="模拟值对象数量")
    parser.add_argument("--binary-inputs", type=int, default=None, help="二进制输入对象数量")
    parser.add_argument("--binary-outputs", type=int, default=None, help="二进制输出对象数量")
    parser.add_argument("--binary-values", type=int, default=None, help="二进制值对象数量")
    parser.add_argument("--multistate-inputs", type=int, default=None, help="多状态输入对象数量")
    parser.add_argument("--multistate-outputs", type=int, default=None, help="多状态输出对象数量")
    parser.add_argument("--multistate-values", type=int, default=None, help="多状态值对象数量")

    parser.add_argument(
        "--generate-config-only", action="store_true",
        help="仅生成 Gateway 配置文件并退出",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )

    return parser.parse_args()


# ---------- Main Entry Point ----------

async def main():
    """Main entry point for the BACnet simulator."""
    args = parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level))

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
    simulators = []

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

    # If only generating config, skip creating simulators
    if args.generate_config_only:
        gateway_config = BACnetSimulator.generate_gateway_config_from_device_configs(
            device_configs,
            num_connectors=args.connectors,
            devices_per_connector=args.devices,
        )
        await handle_config_only_mode(gateway_config, BACnetSimulator.get_protocol_name(), args)
        return

    # Create actual BACnet simulators
    for cfg in device_configs:
        sim = await BACnetSimulator.build_device(cfg)
        simulators.append(sim)

    # Generate and save gateway config(s)
    gateway_config = BACnetSimulator.generate_gateway_config(
        simulators,
        num_connectors=args.connectors,
        devices_per_connector=args.devices,
    )

    config_path = await save_gateway_configs(gateway_config, BACnetSimulator.get_protocol_name(), args)

    # Print summary table
    print("\n" + "=" * 80)
    print(f"{'Device ID':<12} {'Port':<8} {'Name':<25} {'Objects':<10}")
    print("-" * 80)
    for sim in simulators:
        cfg = sim.config
        print(
            f"{cfg.device_id:<12} {cfg.port:<8} "
            f"{sim.device_obj.objectName:<25} {len(sim.objects):<10}"
        )
    print("=" * 80)
    print(f"\nSimulator running. Press Ctrl+C to stop.")
    print(f"Gateway config saved to: {config_path}")
    print()

    # Start data simulation tasks
    tasks = []
    for sim in simulators:
        task = asyncio.create_task(BACnetSimulator.simulate_data(sim, args.update_interval))
        tasks.append(task)

    # Wait for shutdown signal
    stop_event = asyncio.Event()

    def signal_handler(sig, frame):
        log.info("Shutdown signal received...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await stop_event.wait()

    # Cleanup
    log.info("Stopping simulator...")
    for task in tasks:
        task.cancel()
    for sim in simulators:
        try:
            sim.app.close()
        except Exception as e:
            log.warning(f"Error closing device {sim.config.device_id}: {e}")

    log.info("Simulator stopped.")


if __name__ == "__main__":
    asyncio.run(main())
