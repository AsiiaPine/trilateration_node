"""
UWB Localization System - Flexible input/output architecture
"""

from .core import LocalizationEngine, multilateration
from .input_adapters import (
    InputAdapter, SerialInputAdapter, MQTTInputAdapter, 
    UDPInputAdapter, FileInputAdapter
)
from .output_adapters import (
    OutputAdapter, MavlinkOutputAdapter, MavrosOutputAdapter,
    UDPOutputAdapter, FileOutputAdapter, ConsoleOutputAdapter,
    MultiOutputAdapter
)

__version__ = "0.1.0"
