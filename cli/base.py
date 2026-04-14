"""
Base CLI functionality shared across all protocol simulators.
"""

import asyncio
import logging
import signal
import sys
from dataclasses import dataclass
from typing import Optional

from simulators.utils import get_local_ipv4


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@dataclass
class CommonArgs:
    """Common arguments shared across all protocols."""

    # Common parameters
    devices: int
    connectors: int
    objects_per_device: int
    update_interval: float
    ip: str
    gateway_host: Optional[str]
    poll_period: int

    # Control flags
    generate_config_only: bool
    no_data_update: bool  # 禁用数据自动更新
    log_level: str


def add_common_arguments(parser):
    """Add common arguments to a parser."""
    parser.add_argument(
        "--devices", type=int, default=1,
        help="每个连接器的设备数量 (默认: 1)",
    )
    parser.add_argument(
        "--connectors", type=int, default=1,
        help="生成的连接器配置文件数量，每个连接器独立配置指定数量的设备 (默认: 1)",
    )
    parser.add_argument(
        "--objects-per-device", type=int, default=10,
        help="每个设备的对象数量 (默认: 10)",
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
    parser.add_argument(
        "--config-dir", type=str, default="config",
        help="配置文件输出目录 (默认: config/)",
    )
    parser.add_argument(
        "--report-strategy", type=str, default="ON_RECEIVED",
        choices=["ON_RECEIVED", "ON_CHANGE", "ON_REPORT_PERIOD", "ON_CHANGE_OR_REPORT_PERIOD", "DISABLED"],
        help="设备级上报策略 (默认: ON_RECEIVED)",
    )
    parser.add_argument(
        "--report-period", type=int, default=10000,
        help="上报周期，单位毫秒，用于 ON_REPORT_PERIOD 和 ON_CHANGE_OR_REPORT_PERIOD 策略 (默认: 10000)",
    )
    parser.add_argument(
        "--timeseries-report-strategy", type=str, default=None,
        choices=["ON_RECEIVED", "ON_CHANGE", "ON_REPORT_PERIOD", "ON_CHANGE_OR_REPORT_PERIOD", "DISABLED"],
        help="时序数据条目级上报策略 (默认: 使用 --report-strategy 值)",
    )
    parser.add_argument(
        "--timeseries-report-period", type=int, default=None,
        help="时序数据上报周期，单位毫秒，用于 ON_REPORT_PERIOD 和 ON_CHANGE_OR_REPORT_PERIOD 策略 (默认: 使用 --report-period 值)",
    )
    parser.add_argument(
        "--no-data-update", action="store_true",
        help="禁用数据自动更新，保持初始值不变 (默认: 数据会自动变化)",
    )
    parser.add_argument(
        "--generate-config-only", action="store_true",
        help="仅生成 Gateway 配置文件并退出",
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )


def setup_logging(log_level: str) -> None:
    """Set up logging level."""
    logging.getLogger().setLevel(getattr(logging, log_level))


async def run_simulation_loop(
    simulator_class,
    device_configs,
    args,
) -> None:
    """Run the main simulation loop.

    Args:
        simulator_class: The simulator class (e.g., BACnetSimulator)
        device_configs: List of device configurations
        args: Parsed command line arguments
    """
    from simulators.utils import handle_config_only_mode, save_gateway_configs

    log = logging.getLogger(f"{simulator_class.get_protocol_name()}-simulator")
    simulators = []

    # If only generating config, skip creating simulators
    if args.generate_config_only:
        gateway_config = simulator_class.generate_gateway_config_from_device_configs(
            device_configs,
            num_connectors=args.connectors,
            devices_per_connector=args.devices,
            report_strategy=args.report_strategy,
            report_period=args.report_period,
            timeseries_report_strategy=args.timeseries_report_strategy,
            timeseries_report_period=args.timeseries_report_period,
        )
        await handle_config_only_mode(
            gateway_config,
            simulator_class.get_protocol_name(),
            args,
        )
        return

    # Create actual simulators
    for cfg in device_configs:
        sim = await simulator_class.build_device(cfg)
        simulators.append(sim)

    # Generate and save gateway config(s)
    gateway_config = simulator_class.generate_gateway_config(
        simulators,
        num_connectors=args.connectors,
        devices_per_connector=args.devices,
        report_strategy=args.report_strategy,
        report_period=args.report_period,
        timeseries_report_strategy=args.timeseries_report_strategy,
        timeseries_report_period=args.timeseries_report_period,
    )

    config_path = await save_gateway_configs(
        gateway_config,
        simulator_class.get_protocol_name(),
        args,
    )

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

    # Check if data update is disabled
    no_data_update = getattr(args, 'no_data_update', False)
    if no_data_update:
        print("Data update is DISABLED - values will remain constant.")
    else:
        print("Data update is ENABLED - values will change over time.")
    print()

    # Start data simulation tasks (only if not disabled)
    tasks = []
    if not no_data_update:
        for sim in simulators:
            task = asyncio.create_task(
                simulator_class.simulate_data(sim, args.update_interval)
            )
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
    # Only cancel tasks if they were created
    if tasks:
        for task in tasks:
            task.cancel()
    for sim in simulators:
        try:
            sim.app.close()
        except Exception as e:
            log.warning(f"Error closing device {sim.config.device_id}: {e}")

    log.info("Simulator stopped.")
