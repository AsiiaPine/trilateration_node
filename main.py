#!/usr/bin/env python3
"""
Universal UWB Localization Script
Supports flexible input/output adapters for distance measurements and position output.
"""
import time
import signal
import sys
import toml
from typing import Dict, Tuple, Optional, List
from pathlib import Path

from uwb_localizer import (
    LocalizationEngine,
    SerialInputAdapter, MQTTInputAdapter, UDPInputAdapter, FileInputAdapter,
    MavlinkOutputAdapter, MavrosOutputAdapter, UDPOutputAdapter, 
    FileOutputAdapter, ConsoleOutputAdapter, MultiOutputAdapter
)


class UWBLocalizerApp:
    """Main application class."""
    
    def __init__(self, config_path: str = "config.toml"):
        """Initialize application with configuration."""
        self.config = self._load_config(config_path)
        self.engine = None
        self.input_adapter = None
        self.output_adapter = None
        self.running = False
        self.last_position = None
        self.position_history = []
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from TOML file."""
        try:
            with open(config_path, 'r') as f:
                config = toml.load(f)
            print(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            print(f"Config file not found: {config_path}, using defaults")
            return self._default_config()
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return self._default_config()
    
    def _default_config(self) -> dict:
        """Return default configuration."""
        return {
            "localization": {
                "anchor_positions": {
                    "1": [0.0, 0.0, 0.0],
                    "2": [3.0, 0.0, 0.0],
                    "3": [0.0, 3.0, 0.0]
                },
                "calibration_type": "none",
                "calibration_params": [1.0, 0.0],
                "z_sign": 0,
                "min_range": 0.0,
                "max_range": 100.0
            },
            "input": {
                "type": "serial",
                "port": "/dev/ttyUSB0",
                "baud": 460800
            },
            "output": {
                "type": "console",
                "format": "human"
            }
        }
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\nShutting down...")
        self.stop()
        sys.exit(0)
    
    def _parse_anchor_positions(self) -> Dict[int, Tuple[float, float, float]]:
        """Parse anchor positions from config."""
        anchor_positions = {}
        loc_config = self.config.get("localization", {})
        anchors = loc_config.get("anchor_positions", {})
        
        for anchor_id_str, position in anchors.items():
            anchor_id = int(anchor_id_str)
            if isinstance(position, list) and len(position) == 3:
                anchor_positions[anchor_id] = tuple(position)
            else:
                raise ValueError(f"Invalid anchor position for anchor {anchor_id}: {position}")
        
        return anchor_positions
    
    def _create_localization_engine(self) -> LocalizationEngine:
        """Create localization engine from config."""
        loc_config = self.config.get("localization", {})
        anchor_positions = self._parse_anchor_positions()
        
        return LocalizationEngine(
            anchor_positions=anchor_positions,
            calibration_type=loc_config.get("calibration_type", "none"),
            calibration_params=loc_config.get("calibration_params", []),
            z_sign=loc_config.get("z_sign", 0),
            min_range=loc_config.get("min_range", 0.0),
            max_range=loc_config.get("max_range", 100.0)
        )
    
    def _create_input_adapter(self):
        """Create input adapter from config."""
        input_config = self.config.get("input", {})
        adapter_type = input_config.get("type", "serial").lower()
        
        if adapter_type == "serial":
            return SerialInputAdapter(
                port=input_config.get("port", "/dev/ttyUSB0"),
                baud=input_config.get("baud", 460800),
                timeout=input_config.get("timeout", 1.0)
            )
        elif adapter_type == "mqtt":
            return MQTTInputAdapter(
                broker=input_config.get("broker", "localhost"),
                port=input_config.get("port", 1883),
                topic=input_config.get("topic", "uwb/distances")
            )
        elif adapter_type == "udp":
            return UDPInputAdapter(
                host=input_config.get("host", "0.0.0.0"),
                port=input_config.get("port", 5005)
            )
        elif adapter_type == "file":
            return FileInputAdapter(
                filepath=input_config.get("filepath", "distances.json"),
                poll_interval=input_config.get("poll_interval", 1.0)
            )
        else:
            raise ValueError(f"Unknown input adapter type: {adapter_type}")
    
    def _create_output_adapter(self):
        """Create output adapter(s) from config."""
        output_config = self.config.get("output", {})
        adapter_type = output_config.get("type", "console").lower()
        
        adapters = []
        
        # Support multiple outputs (comma-separated or list)
        if isinstance(adapter_type, str) and "," in adapter_type:
            adapter_types = [t.strip() for t in adapter_type.split(",")]
        elif isinstance(adapter_type, list):
            adapter_types = adapter_type
        else:
            adapter_types = [adapter_type]
        
        for adapter_type in adapter_types:
            if adapter_type == "mavlink":
                adapters.append(MavlinkOutputAdapter(
                    connection_string=output_config.get("connection_string", "udp:127.0.0.1:14550"),
                    system_id=output_config.get("system_id", 1),
                    component_id=output_config.get("component_id", 1)
                ))
            elif adapter_type == "mavros":
                adapters.append(MavrosOutputAdapter(
                    topic_prefix=output_config.get("topic_prefix", "mavros"),
                    frame_id=output_config.get("frame_id", "map")
                ))
            elif adapter_type == "udp":
                adapters.append(UDPOutputAdapter(
                    host=output_config.get("host", "127.0.0.1"),
                    port=output_config.get("port", 5006)
                ))
            elif adapter_type == "file":
                adapters.append(FileOutputAdapter(
                    filepath=output_config.get("filepath", "positions.jsonl"),
                    mode=output_config.get("mode", "a")
                ))
            elif adapter_type == "console":
                adapters.append(ConsoleOutputAdapter(
                    format=output_config.get("format", "human")
                ))
            else:
                print(f"Warning: Unknown output adapter type: {adapter_type}, skipping")
        
        if not adapters:
            adapters.append(ConsoleOutputAdapter())
        
        if len(adapters) == 1:
            return adapters[0]
        else:
            return MultiOutputAdapter(adapters)
    
    def _on_distance_update(self, distances: Dict[int, float]):
        """Callback for when new distance measurements arrive."""
        if not self.engine:
            return
        
        # Apply calibration
        calibrated_distances = {}
        for anchor_id, raw_distance in distances.items():
            calibrated = self.engine.calibrate(raw_distance)
            if self.engine.validate_range(calibrated):
                calibrated_distances[anchor_id] = calibrated
        
        # Calculate position
        position = self.engine.calculate_position(calibrated_distances)
        
        if position:
            self.last_position = position
            timestamp = time.time()
            
            # Send to output adapter
            if self.output_adapter:
                self.output_adapter.send_position(position, timestamp)
            
            # Store in history (optional, for debugging)
            self.position_history.append((timestamp, position))
            if len(self.position_history) > 1000:  # Keep last 1000 positions
                self.position_history.pop(0)
        else:
            print(f"Warning: Could not calculate position from distances: {calibrated_distances}")
    
    def start(self):
        """Start the localization system."""
        print("Initializing UWB Localization System...")
        
        # Create localization engine
        self.engine = self._create_localization_engine()
        print(f"Localization engine initialized with {len(self.engine.anchor_positions)} anchors")
        
        # Create input adapter
        self.input_adapter = self._create_input_adapter()
        self.input_adapter.start(self._on_distance_update)
        print(f"Input adapter started: {type(self.input_adapter).__name__}")
        
        # Create output adapter
        self.output_adapter = self._create_output_adapter()
        print(f"Output adapter initialized: {type(self.output_adapter).__name__}")
        
        self.running = True
        print("UWB Localization System started. Press Ctrl+C to stop.")
    
    def stop(self):
        """Stop the localization system."""
        self.running = False
        
        if self.input_adapter:
            self.input_adapter.stop()
            print("Input adapter stopped")
        
        if self.output_adapter:
            self.output_adapter.close()
            print("Output adapter closed")
        
        print("UWB Localization System stopped")
    
    def run(self):
        """Run the main loop."""
        self.start()
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Universal UWB Localization Script")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.toml",
        help="Path to configuration file (default: config.toml)"
    )
    
    args = parser.parse_args()
    
    app = UWBLocalizerApp(config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()
