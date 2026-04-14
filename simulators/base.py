"""
Base classes for protocol simulators.

Provides abstract interfaces for creating protocol-specific simulators
(BACnet, Modbus, etc.) for ThingsBoard Gateway performance testing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class BaseDeviceConfig:
    """Base configuration for a simulated device.

    Protocol-specific implementations should extend this class
    to add protocol-specific configuration fields.
    """
    device_id: int
    port: int
    ip: str = "0.0.0.0"
    host: Optional[str] = None  # Gateway connection host (defaults to ip if not set)
    object_count: int = 10
    poll_period: int = 10000  # in milliseconds

    def get_gateway_host(self) -> str:
        """Get the host address that Gateway should use to connect to this device."""
        if self.host:
            return self.host
        elif self.ip == "0.0.0.0":
            return "127.0.0.1"
        return self.ip


@dataclass
class BaseSimulatedDevice:
    """Base class for a simulated device.

    Protocol-specific implementations should extend this class
    to add protocol-specific device and object representations.
    """
    config: BaseDeviceConfig
    app: Any = None  # Protocol-specific application/handler
    device_obj: Any = None  # Protocol-specific device object
    objects: list = field(default_factory=list)  # List of simulated objects


class BaseSimulator(ABC):
    """Abstract base class for protocol simulators.

    Protocol-specific simulators (BACnet, Modbus, etc.) must implement
    the methods defined in this class to provide a consistent interface.
    """

    @staticmethod
    @abstractmethod
    def get_protocol_name() -> str:
        """Return the protocol name (e.g., 'bacnet', 'modbus')."""
        pass

    @staticmethod
    @abstractmethod
    def get_protocol_type() -> str:
        """Return the protocol type for Gateway config (e.g., 'bacnet', 'modbus')."""
        pass

    @staticmethod
    @abstractmethod
    def create_device_config(
        device_id: int,
        port: int,
        object_count: int,
        **kwargs
    ) -> BaseDeviceConfig:
        """Create a device configuration for this protocol."""
        pass

    @staticmethod
    @abstractmethod
    async def build_device(cfg: BaseDeviceConfig) -> BaseSimulatedDevice:
        """Build a complete simulated device with all objects."""
        pass

    @staticmethod
    @abstractmethod
    async def simulate_data(device: BaseSimulatedDevice, interval: float):
        """Run data simulation loop for a device."""
        pass

    @classmethod
    @abstractmethod
    def generate_gateway_config(
        cls,
        devices: list[BaseSimulatedDevice],
        gateway_ip: str = "0.0.0.0",
        gateway_port: int = 47808,
        num_connectors: int = 1,
        devices_per_connector: int = 1,
    ) -> Dict:
        """Generate Gateway connector configuration.

        Args:
            devices: List of simulated devices
            gateway_ip: Gateway binding IP address
            gateway_port: Gateway binding port (protocol-specific default)
            num_connectors: Number of connector configs to generate
            devices_per_connector: Number of devices per connector

        Returns:
            Dictionary containing connector configuration(s)
        """
        pass

    @classmethod
    @abstractmethod
    def generate_object_list(cls, cfg: BaseDeviceConfig) -> list:
        """Generate object list from device config for Gateway config.

        Returns a list of object definitions that will be included in
        the Gateway connector configuration.
        """
        pass
