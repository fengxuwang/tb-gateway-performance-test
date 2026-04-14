"""
BACnet Simulator for ThingsBoard Gateway Performance Testing.

Simulates multiple BACnet devices, each with configurable numbers of
analog/binary/multistate objects. Compatible with the ThingsBoard Gateway
BACnet connector (bacpypes3-based).
"""

from .simulator import (
    BACnetSimulator,
    BACnetDeviceConfig,
    BACnetSimulatedDevice,
    BACnetSimulatedObject,
    ANALOG_UNITS,
    MULTI_STATE_LABELS,
    distribute_objects,
)

__all__ = [
    "BACnetSimulator",
    "BACnetDeviceConfig",
    "BACnetSimulatedDevice",
    "BACnetSimulatedObject",
    "ANALOG_UNITS",
    "MULTI_STATE_LABELS",
    "distribute_objects",
]
