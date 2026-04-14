"""
BACnet Simulator implementation.

Provides BACnet device simulation with configurable objects and data simulation.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Optional

from bacpypes3.basetypes import EngineeringUnits
from bacpypes3.ipv4.app import NormalApplication
from bacpypes3.local.analog import (
    AnalogInputObject,
    AnalogOutputObject,
    AnalogValueObject,
)
from bacpypes3.local.binary import (
    BinaryInputObject,
    BinaryOutputObject,
    BinaryValueObject,
)
from bacpypes3.local.device import DeviceObject
from bacpypes3.local.multistate import (
    MultiStateInputObject,
    MultiStateOutputObject,
    MultiStateValueObject,
)
from bacpypes3.pdu import Address

from ..base import BaseSimulator, BaseDeviceConfig, BaseSimulatedDevice

log = logging.getLogger("bacnet-simulator")

# ---------- Constants ----------

ANALOG_UNITS = [
    EngineeringUnits.degreesCelsius,
    EngineeringUnits.percentRelativeHumidity,
    EngineeringUnits.pascals,
    EngineeringUnits.kilopascals,
    EngineeringUnits.volts,
    EngineeringUnits.amperes,
    EngineeringUnits.watts,
    EngineeringUnits.litersPerMinute,
    EngineeringUnits.metersPerSecond,
    EngineeringUnits.hertz,
]

MULTI_STATE_LABELS = {
    "HVAC Mode": ["Off", "Cooling", "Heating", "Auto"],
    "Fan Speed": ["Off", "Low", "Medium", "High"],
    "Damper Position": ["Closed", "Quarter", "Half", "ThreeQuarter", "Full"],
    "Alarm Level": ["Normal", "Advisory", "Warning", "Critical"],
    "Pump Status": ["Stopped", "Starting", "Running", "Fault"],
}


# ---------- Configuration ----------

@dataclass
class BACnetDeviceConfig(BaseDeviceConfig):
    """Configuration for a BACnet simulated device."""

    # BACnet-specific object counts
    analog_input_count: int = 0
    analog_output_count: int = 0
    analog_value_count: int = 0
    binary_input_count: int = 0
    binary_output_count: int = 0
    binary_value_count: int = 0
    multistate_input_count: int = 0
    multistate_output_count: int = 0
    multistate_value_count: int = 0


@dataclass
class BACnetSimulatedObject:
    """A simulated BACnet object with metadata for data simulation."""

    obj: object  # The actual BACnet object
    object_type: str  # BACnet object type (e.g., "analogInput")
    object_id: int  # BACnet object identifier
    data_type: str  # "analog" | "binary" | "multistate"
    min_val: float = 0.0  # For analog objects
    max_val: float = 100.0  # For analog objects
    step: float = 1.0  # For analog objects
    states: int = 4  # For multistate objects


@dataclass
class BACnetSimulatedDevice(BaseSimulatedDevice):
    """A simulated BACnet device."""

    config: BACnetDeviceConfig
    app: NormalApplication = None
    device_obj: DeviceObject = None
    objects: list[BACnetSimulatedObject] = field(default_factory=list)


# ---------- Utility Functions ----------

def distribute_objects(total: int) -> dict:
    """Distribute total objects across types with reasonable defaults."""
    if total <= 3:
        return {
            "analog_input": total,
            "binary_input": 0,
            "analog_value": 0,
            "binary_output": 0,
            "multistate_input": 0,
            "analog_output": 0,
            "binary_value": 0,
            "multistate_output": 0,
            "multistate_value": 0,
        }

    # Default distribution ratios (mimics typical BACnet building automation)
    ratios = {
        "analog_input": 0.35,
        "binary_input": 0.15,
        "analog_value": 0.15,
        "analog_output": 0.10,
        "binary_output": 0.08,
        "binary_value": 0.05,
        "multistate_input": 0.05,
        "multistate_output": 0.04,
        "multistate_value": 0.03,
    }

    distributed = {}
    remaining = total
    keys = list(ratios.keys())

    for i, key in enumerate(keys):
        if i == len(keys) - 1:
            distributed[key] = max(0, remaining)
        else:
            count = max(0, round(total * ratios[key]))
            distributed[key] = count
            remaining -= count

    return distributed


def create_device_config(
    device_id: int,
    port: int,
    object_count: int,
    distribution: Optional[dict] = None,
    poll_period: int = 10000,
    host: Optional[str] = None,
    ip: str = "0.0.0.0",
) -> BACnetDeviceConfig:
    """Create a BACnetDeviceConfig with object counts from distribution or auto."""
    cfg = BACnetDeviceConfig(
        device_id=device_id,
        port=port,
        object_count=object_count,
        poll_period=poll_period,
        host=host,
        ip=ip,
    )

    if distribution is None:
        distribution = distribute_objects(object_count)

    cfg.analog_input_count = distribution.get("analog_input", 0)
    cfg.binary_input_count = distribution.get("binary_input", 0)
    cfg.analog_value_count = distribution.get("analog_value", 0)
    cfg.analog_output_count = distribution.get("analog_output", 0)
    cfg.binary_output_count = distribution.get("binary_output", 0)
    cfg.binary_value_count = distribution.get("binary_value", 0)
    cfg.multistate_input_count = distribution.get("multistate_input", 0)
    cfg.multistate_output_count = distribution.get("multistate_output", 0)
    cfg.multistate_value_count = distribution.get("multistate_value", 0)

    return cfg


# ---------- Object Factory ----------

def create_analog_object(
    object_type: str,
    obj_id: int,
    device_name: str,
    unit: EngineeringUnits,
) -> BACnetSimulatedObject:
    """Create an analog BACnet object (AI/AO/AV)."""
    cls_map = {
        "analog_input": AnalogInputObject,
        "analog_output": AnalogOutputObject,
        "analog_value": AnalogValueObject,
    }
    type_map = {
        "analog_input": "analogInput",
        "analog_output": "analogOutput",
        "analog_value": "analogValue",
    }

    cls = cls_map[object_type]
    bac_type = type_map[object_type]
    obj_name = f"{device_name}_{bac_type}_{obj_id}"

    # Generate realistic initial values based on unit
    if unit in (EngineeringUnits.degreesCelsius,):
        initial = random.uniform(18, 28)
        min_v, max_v, step = 10, 40, 0.5
    elif unit in (EngineeringUnits.percentRelativeHumidity,):
        initial = random.uniform(30, 70)
        min_v, max_v, step = 0, 100, 2.0
    elif unit in (EngineeringUnits.pascals, EngineeringUnits.kilopascals):
        initial = random.uniform(95, 105) if unit == EngineeringUnits.kilopascals else random.uniform(100, 200)
        min_v, max_v, step = 80, 120, 1.0
    elif unit in (EngineeringUnits.volts,):
        initial = random.uniform(220, 240)
        min_v, max_v, step = 200, 260, 5.0
    elif unit in (EngineeringUnits.amperes,):
        initial = random.uniform(1, 15)
        min_v, max_v, step = 0, 30, 0.5
    elif unit in (EngineeringUnits.watts,):
        initial = random.uniform(100, 5000)
        min_v, max_v, step = 0, 10000, 100
    elif unit in (EngineeringUnits.litersPerMinute,):
        initial = random.uniform(5, 50)
        min_v, max_v, step = 0, 100, 1.0
    elif unit in (EngineeringUnits.metersPerSecond,):
        initial = random.uniform(0, 5)
        min_v, max_v, step = 0, 20, 0.2
    elif unit in (EngineeringUnits.hertz,):
        initial = random.uniform(49, 51)
        min_v, max_v, step = 45, 55, 0.1
    else:
        initial = random.uniform(0, 100)
        min_v, max_v, step = 0, 100, 1.0

    obj = cls(
        objectIdentifier=(bac_type, obj_id),
        objectName=obj_name,
        presentValue=initial,
        units=unit,
        description=obj_name,
        minPresValue=min_v,
        maxPresValue=max_v,
    )

    return BACnetSimulatedObject(
        obj=obj,
        object_type=bac_type,
        object_id=obj_id,
        data_type="analog",
        min_val=min_v,
        max_val=max_v,
        step=step,
    )


def create_binary_object(
    object_type: str,
    obj_id: int,
    device_name: str,
) -> BACnetSimulatedObject:
    """Create a binary BACnet object (BI/BO/BV)."""
    cls_map = {
        "binary_input": BinaryInputObject,
        "binary_output": BinaryOutputObject,
        "binary_value": BinaryValueObject,
    }
    type_map = {
        "binary_input": "binaryInput",
        "binary_output": "binaryOutput",
        "binary_value": "binaryValue",
    }

    cls = cls_map[object_type]
    bac_type = type_map[object_type]
    obj_name = f"{device_name}_{bac_type}_{obj_id}"
    initial = random.choice(["active", "inactive"])

    obj = cls(
        objectIdentifier=(bac_type, obj_id),
        objectName=obj_name,
        presentValue=initial,
        description=obj_name,
    )

    return BACnetSimulatedObject(
        obj=obj,
        object_type=bac_type,
        object_id=obj_id,
        data_type="binary",
    )


def create_multistate_object(
    object_type: str,
    obj_id: int,
    device_name: str,
) -> BACnetSimulatedObject:
    """Create a multistate BACnet object (MSI/MSO/MSV)."""
    cls_map = {
        "multistate_input": MultiStateInputObject,
        "multistate_output": MultiStateOutputObject,
        "multistate_value": MultiStateValueObject,
    }
    type_map = {
        "multistate_input": "multiStateInput",
        "multistate_output": "multiStateOutput",
        "multistate_value": "multiStateValue",
    }

    cls = cls_map[object_type]
    bac_type = type_map[object_type]
    obj_name = f"{device_name}_{bac_type}_{obj_id}"

    labels_name = random.choice(list(MULTI_STATE_LABELS.keys()))
    states_list = MULTI_STATE_LABELS[labels_name]
    num_states = len(states_list)
    initial = random.randint(1, num_states)

    obj = cls(
        objectIdentifier=(bac_type, obj_id),
        objectName=obj_name,
        presentValue=initial,
        numberOfStates=num_states,
        stateText=states_list,
        description=f"{obj_name} ({labels_name})",
    )

    return BACnetSimulatedObject(
        obj=obj,
        object_type=bac_type,
        object_id=obj_id,
        data_type="multistate",
        states=num_states,
    )


# ---------- Device Builder ----------

async def build_simulated_device(cfg: BACnetDeviceConfig) -> BACnetSimulatedDevice:
    """Build a complete simulated BACnet device with all objects."""
    sim = BACnetSimulatedDevice(config=cfg)

    # Generate device name with 4-digit sequential number starting from 0001
    device_seq = cfg.device_id - 100 + 1  # Calculate sequence from device_id (base 100)
    device_name = f"BACnet-Sim-{device_seq:04d}"

    sim.device_obj = DeviceObject(
        objectIdentifier=("device", cfg.device_id),
        objectName=device_name,
        vendorIdentifier=999,
        vendorName="BACnetSimulator",
        modelName="Performance Test Device",
        firmwareRevision="1.0.0",
        applicationSoftwareVersion="1.0.0",
        protocolVersion=1,
        protocolRevision=22,
        maxApduLengthAccepted=65535,  # Increase APDU size for large object lists
        segmentationSupported="segmentedBoth",
        description=f"Simulated BACnet device #{cfg.device_id} with {cfg.object_count} objects",
    )

    address = Address(f"{cfg.ip}:{cfg.port}")
    sim.app = NormalApplication(device_object=sim.device_obj, local_address=address)

    obj_id_counter = 1
    unit_index = 0

    def next_unit():
        nonlocal unit_index
        u = ANALOG_UNITS[unit_index % len(ANALOG_UNITS)]
        unit_index += 1
        return u

    # Create analog inputs
    log.info(f"Creating {cfg.analog_input_count} analog inputs...")
    for i in range(cfg.analog_input_count):
        sim_obj = create_analog_object("analog_input", obj_id_counter, device_name, next_unit())
        sim.app.add_object(sim_obj.obj)
        sim.objects.append(sim_obj)
        obj_id_counter += 1
        if (i + 1) % 10 == 0:
            log.info(f"  Created {i + 1}/{cfg.analog_input_count} analog inputs")

    # Create analog outputs
    for i in range(cfg.analog_output_count):
        sim_obj = create_analog_object("analog_output", obj_id_counter, device_name, next_unit())
        sim.app.add_object(sim_obj.obj)
        sim.objects.append(sim_obj)
        obj_id_counter += 1

    # Create analog values
    for i in range(cfg.analog_value_count):
        sim_obj = create_analog_object("analog_value", obj_id_counter, device_name, next_unit())
        sim.app.add_object(sim_obj.obj)
        sim.objects.append(sim_obj)
        obj_id_counter += 1

    # Create binary inputs
    for i in range(cfg.binary_input_count):
        sim_obj = create_binary_object("binary_input", obj_id_counter, device_name)
        sim.app.add_object(sim_obj.obj)
        sim.objects.append(sim_obj)
        obj_id_counter += 1

    # Create binary outputs
    for i in range(cfg.binary_output_count):
        sim_obj = create_binary_object("binary_output", obj_id_counter, device_name)
        sim.app.add_object(sim_obj.obj)
        sim.objects.append(sim_obj)
        obj_id_counter += 1

    # Create binary values
    for i in range(cfg.binary_value_count):
        sim_obj = create_binary_object("binary_value", obj_id_counter, device_name)
        sim.app.add_object(sim_obj.obj)
        sim.objects.append(sim_obj)
        obj_id_counter += 1

    # Create multistate inputs
    for i in range(cfg.multistate_input_count):
        sim_obj = create_multistate_object("multistate_input", obj_id_counter, device_name)
        sim.app.add_object(sim_obj.obj)
        sim.objects.append(sim_obj)
        obj_id_counter += 1

    # Create multistate outputs
    for i in range(cfg.multistate_output_count):
        sim_obj = create_multistate_object("multistate_output", obj_id_counter, device_name)
        sim.app.add_object(sim_obj.obj)
        sim.objects.append(sim_obj)
        obj_id_counter += 1

    # Create multistate values
    for i in range(cfg.multistate_value_count):
        sim_obj = create_multistate_object("multistate_value", obj_id_counter, device_name)
        sim.app.add_object(sim_obj.obj)
        sim.objects.append(sim_obj)
        obj_id_counter += 1

    return sim


# ---------- Data Simulation ----------

async def simulate_analog(sim_obj: BACnetSimulatedObject):
    """Random walk an analog value within bounds."""
    val = float(sim_obj.obj.presentValue)
    change = random.uniform(-sim_obj.step, sim_obj.step)
    new_val = val + change
    new_val = max(sim_obj.min_val, min(sim_obj.max_val, new_val))
    sim_obj.obj.presentValue = round(new_val, 2)


async def simulate_binary(sim_obj: BACnetSimulatedObject):
    """Occasionally flip binary state."""
    if random.random() < 0.1:  # 10% chance to toggle
        current = str(sim_obj.obj.presentValue)
        sim_obj.obj.presentValue = "inactive" if current == "active" else "active"


async def simulate_multistate(sim_obj: BACnetSimulatedObject):
    """Occasionally change multistate value."""
    if random.random() < 0.05:  # 5% chance to change
        new_state = random.randint(1, sim_obj.states)
        sim_obj.obj.presentValue = new_state


async def data_simulation_loop(device: BACnetSimulatedDevice, interval: float):
    """Continuously update simulated data for a single device."""
    while True:
        for sim_obj in device.objects:
            if sim_obj.data_type == "analog":
                await simulate_analog(sim_obj)
            elif sim_obj.data_type == "binary":
                await simulate_binary(sim_obj)
            elif sim_obj.data_type == "multistate":
                await simulate_multistate(sim_obj)
        await asyncio.sleep(interval)


# ---------- Gateway Config Generator ----------

def generate_object_list(cfg: BACnetDeviceConfig) -> list:
    """Generate BACnet object list from device config."""
    objects = []

    obj_types = [
        ("analogInput", cfg.analog_input_count),
        ("analogOutput", cfg.analog_output_count),
        ("analogValue", cfg.analog_value_count),
        ("binaryInput", cfg.binary_input_count),
        ("binaryOutput", cfg.binary_output_count),
        ("binaryValue", cfg.binary_value_count),
        ("multistateInput", cfg.multistate_input_count),
        ("multistateOutput", cfg.multistate_output_count),
        ("multistateValue", cfg.multistate_value_count),
    ]

    for obj_type, count in obj_types:
        for i in range(1, count + 1):
            objects.append({
                "object_type": obj_type,
                "object_id": str(i),
            })

    return objects


def generate_gateway_config(
    devices: list[BACnetSimulatedDevice],
    gateway_ip: str = "0.0.0.0",
    gateway_port: int = 47808,
    num_connectors: int = 1,
    devices_per_connector: int = 1,
    report_strategy: str = "ON_RECEIVED",
    report_period: int = 10000,
    timeseries_report_strategy: str = None,
    timeseries_report_period: int = None,
) -> dict:
    """Generate a ThingsBoard Gateway BACnet connector configuration.

    Args:
        devices: List of ALL simulated devices (from all connectors)
        gateway_ip: Gateway binding IP address
        gateway_port: Gateway binding port
        num_connectors: Number of connector configs to generate
        devices_per_connector: Number of devices per connector
        report_strategy: Device-level report strategy (default: ON_RECEIVED)
        report_period: Device-level report period in milliseconds (default: 10000)
        timeseries_report_strategy: Timeseries entry-level report strategy (default: report_strategy)
        timeseries_report_period: Timeseries entry-level report period in milliseconds (default: report_period)

    Returns:
        Dictionary containing connector configuration(s)
    """
    connectors = []

    for connector_idx in range(num_connectors):
        # Calculate device range for this connector
        start_idx = connector_idx * devices_per_connector
        end_idx = start_idx + devices_per_connector
        connector_devices = devices[start_idx:end_idx]

        if not connector_devices:
            continue

        # Each connector needs unique port and objectIdentifier
        connector_port = gateway_port + connector_idx
        connector_object_id = 599 + connector_idx

        config = {
            "application": {
                "objectName": f"TB_gateway_connector_{connector_idx + 1}",
                "host": gateway_ip,
                "port": str(connector_port),
                "mask": "24",
                "objectIdentifier": connector_object_id,
                "maxApduLengthAccepted": 65535,  # Match simulator APDU size
                "segmentationSupported": "segmentedBoth",
                "vendorIdentifier": 15,
                "deviceDiscoveryTimeoutInSec": 5,
                "networkNumber": 0,
                "networkNumberQuality": "configured",
                "devicesDiscoverPeriodSeconds": 30,
            },
            "devices": [],
        }

        for sim in connector_devices:
            cfg = sim.config
            device_name = sim.device_obj.objectName

            attributes = []
            timeseries = []

            # Put all objects in timeseries for better data history tracking
            ts_strategy = timeseries_report_strategy or report_strategy
            ts_period = timeseries_report_period or report_period
            for i, sim_obj in enumerate(sim.objects):
                entry = {
                    "key": f"{sim_obj.object_type}_{sim_obj.object_id}",
                    "objectType": sim_obj.object_type,
                    "objectId": str(sim_obj.object_id),
                    "propertyId": "presentValue",
                    "reportStrategy": {
                        "type": ts_strategy
                    },
                }
                # Add reportPeriod for strategies that require it
                if ts_strategy in ("ON_REPORT_PERIOD", "ON_CHANGE_OR_REPORT_PERIOD"):
                    entry["reportStrategy"]["reportPeriod"] = ts_period
                timeseries.append(entry)

            # Build device-level report strategy
            device_report_strategy = {
                "type": report_strategy
            }
            if report_strategy in ("ON_REPORT_PERIOD", "ON_CHANGE_OR_REPORT_PERIOD"):
                device_report_strategy["reportPeriod"] = report_period

            device_config = {
                "deviceInfo": {
                    "deviceNameExpression": f"BACnet Device ${{objectName}}",
                    "deviceProfileExpression": "default",
                    "deviceNameExpressionSource": "expression",
                    "deviceProfileExpressionSource": "constant",
                },
                "host": cfg.get_gateway_host(),
                "port": str(cfg.port),
                "pollPeriod": cfg.poll_period,
                "attributes": attributes,
                "timeseries": timeseries,
                "attributeUpdates": [],
                "serverSideRpc": [],
                "reportStrategy": device_report_strategy,
            }
            config["devices"].append(device_config)

        connectors.append(config)

    # Return a config structure that can contain multiple connectors
    if num_connectors == 1:
        # For backward compatibility, return single config directly
        return connectors[0]
    else:
        # Return multiple configs with metadata
        return {
            "connectors": connectors,
            "count": len(connectors),
        }


def generate_gateway_config_from_device_configs(
    device_configs: list[BACnetDeviceConfig],
    gateway_ip: str = "0.0.0.0",
    gateway_port: int = 47808,
    num_connectors: int = 1,
    devices_per_connector: int = 1,
    report_strategy: str = "ON_RECEIVED",
    report_period: int = 10000,
    timeseries_report_strategy: str = None,
    timeseries_report_period: int = None,
) -> dict:
    """Generate gateway connector configurations from device configs (without simulators).

    This is useful for generating configuration files without actually
    creating the BACnet device simulators.

    Args:
        device_configs: List of device configurations
        gateway_ip: Gateway binding IP address
        gateway_port: Gateway binding port
        num_connectors: Number of connector configs to generate
        devices_per_connector: Number of devices per connector
        report_strategy: Device-level report strategy (default: ON_RECEIVED)
        report_period: Device-level report period in milliseconds (default: 10000)
        timeseries_report_strategy: Timeseries entry-level report strategy (default: report_strategy)
        timeseries_report_period: Timeseries entry-level report period in milliseconds (default: report_period)
    """
    connectors = []

    for connector_idx in range(num_connectors):
        # Calculate device range for this connector
        start_idx = connector_idx * devices_per_connector
        end_idx = start_idx + devices_per_connector
        connector_device_configs = device_configs[start_idx:end_idx]

        if not connector_device_configs:
            continue

        # Each connector needs unique port and objectIdentifier
        connector_port = gateway_port + connector_idx
        connector_object_id = 599 + connector_idx

        config = {
            "application": {
                "objectName": f"TB_gateway_connector_{connector_idx + 1}",
                "host": gateway_ip,
                "port": str(connector_port),
                "mask": "24",
                "objectIdentifier": connector_object_id,
                "maxApduLengthAccepted": 65535,  # Match simulator APDU size
                "segmentationSupported": "segmentedBoth",
                "vendorIdentifier": 15,
                "deviceDiscoveryTimeoutInSec": 5,
                "networkNumber": 0,
                "networkNumberQuality": "configured",
                "devicesDiscoverPeriodSeconds": 30,
            },
            "devices": [],
        }

        for cfg in connector_device_configs:
            # Generate device name from config
            device_seq = cfg.device_id - 100 + 1
            device_name = f"BACnet-Sim-{device_seq:04d}"

            attributes = []
            timeseries = []

            # Generate object list from device config
            objects = generate_object_list(cfg)

            # Put all objects in timeseries for better data history tracking
            ts_strategy = timeseries_report_strategy or report_strategy
            ts_period = timeseries_report_period or report_period
            for obj in objects:
                entry = {
                    "key": f"{obj['object_type']}_{obj['object_id']}",
                    "objectType": obj['object_type'],
                    "objectId": obj['object_id'],
                    "propertyId": "presentValue",
                    "reportStrategy": {
                        "type": ts_strategy
                    },
                }
                # Add reportPeriod for strategies that require it
                if ts_strategy in ("ON_REPORT_PERIOD", "ON_CHANGE_OR_REPORT_PERIOD"):
                    entry["reportStrategy"]["reportPeriod"] = ts_period
                timeseries.append(entry)

            # Build device-level report strategy
            device_report_strategy = {
                "type": report_strategy
            }
            if report_strategy in ("ON_REPORT_PERIOD", "ON_CHANGE_OR_REPORT_PERIOD"):
                device_report_strategy["reportPeriod"] = report_period

            device_config = {
                "deviceInfo": {
                    "deviceNameExpression": f"BACnet Device ${{objectName}}",
                    "deviceProfileExpression": "default",
                    "deviceNameExpressionSource": "expression",
                    "deviceProfileExpressionSource": "constant",
                },
                "host": cfg.get_gateway_host(),
                "port": str(cfg.port),
                "pollPeriod": cfg.poll_period,
                "attributes": attributes,
                "timeseries": timeseries,
                "attributeUpdates": [],
                "serverSideRpc": [],
                "reportStrategy": device_report_strategy,
            }
            config["devices"].append(device_config)

        connectors.append(config)

    # Return a config structure that can contain multiple connectors
    if num_connectors == 1:
        # For backward compatibility, return single config directly
        return connectors[0]
    else:
        # Return multiple configs with metadata
        return {
            "connectors": connectors,
            "count": len(connectors),
        }


# ---------- BACnet Simulator Class ----------

class BACnetSimulator(BaseSimulator):
    """BACnet protocol simulator implementation."""

    @staticmethod
    def get_protocol_name() -> str:
        return "bacnet"

    @staticmethod
    def get_protocol_type() -> str:
        return "bacnet"

    @staticmethod
    def create_device_config(
        device_id: int,
        port: int,
        object_count: int,
        **kwargs,
    ) -> BACnetDeviceConfig:
        """Create a BACnet device configuration.

        Keyword arguments:
            distribution: Optional dict with object type counts
            poll_period: Poll period in milliseconds
            host: Gateway connection host
            ip: Device binding IP address
        """
        return create_device_config(
            device_id=device_id,
            port=port,
            object_count=object_count,
            distribution=kwargs.get("distribution"),
            poll_period=kwargs.get("poll_period", 10000),
            host=kwargs.get("host"),
            ip=kwargs.get("ip", "0.0.0.0"),
        )

    @staticmethod
    async def build_device(cfg: BACnetDeviceConfig) -> BACnetSimulatedDevice:
        """Build a complete simulated BACnet device with all objects."""
        return await build_simulated_device(cfg)

    @staticmethod
    async def simulate_data(device: BACnetSimulatedDevice, interval: float):
        """Run data simulation loop for a BACnet device."""
        await data_simulation_loop(device, interval)

    @classmethod
    def generate_gateway_config(
        cls,
        devices: list[BACnetSimulatedDevice],
        gateway_ip: str = "0.0.0.0",
        gateway_port: int = 47808,
        num_connectors: int = 1,
        devices_per_connector: int = 1,
        report_strategy: str = "ON_RECEIVED",
        report_period: int = 10000,
        timeseries_report_strategy: str = None,
        timeseries_report_period: int = None,
    ) -> dict:
        """Generate Gateway connector configuration for BACnet devices."""
        return generate_gateway_config(
            devices=devices,
            gateway_ip=gateway_ip,
            gateway_port=gateway_port,
            num_connectors=num_connectors,
            devices_per_connector=devices_per_connector,
            report_strategy=report_strategy,
            report_period=report_period,
            timeseries_report_strategy=timeseries_report_strategy,
            timeseries_report_period=timeseries_report_period,
        )

    @classmethod
    def generate_object_list(cls, cfg: BACnetDeviceConfig) -> list:
        """Generate BACnet object list from device config."""
        return generate_object_list(cfg)

    @classmethod
    def generate_gateway_config_from_device_configs(
        cls,
        device_configs: list[BACnetDeviceConfig],
        gateway_ip: str = "0.0.0.0",
        gateway_port: int = 47808,
        num_connectors: int = 1,
        devices_per_connector: int = 1,
        report_strategy: str = "ON_RECEIVED",
        report_period: int = 10000,
        timeseries_report_strategy: str = None,
        timeseries_report_period: int = None,
    ) -> dict:
        """Generate gateway configuration from device configs (without simulators)."""
        return generate_gateway_config_from_device_configs(
            device_configs=device_configs,
            gateway_ip=gateway_ip,
            gateway_port=gateway_port,
            num_connectors=num_connectors,
            devices_per_connector=devices_per_connector,
            report_strategy=report_strategy,
            report_period=report_period,
            timeseries_report_strategy=timeseries_report_strategy,
            timeseries_report_period=timeseries_report_period,
        )
