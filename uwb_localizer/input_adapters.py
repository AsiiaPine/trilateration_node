"""
Input adapters for receiving distance measurements from various sources.
"""
import serial
import struct
import json
import socket
import threading
import time
from typing import Dict, Optional, Callable
from abc import ABC, abstractmethod


class InputAdapter(ABC):
    """Base class for input adapters."""
    
    @abstractmethod
    def start(self, callback: Callable[[Dict[int, float]], None]):
        """Start receiving data and call callback with distance measurements."""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop receiving data."""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Check if adapter is running."""
        pass


class SerialInputAdapter(InputAdapter):
    """Serial port input adapter (from RTK-DW1000 implementation)."""
    
    def __init__(self, port: str, baud: int = 460800, timeout: float = 1.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None
        self.running = False
        self.callback = None
        self.thread = None
        self.buffer = CircularBuffer(100, element_size=7)
    
    def start(self, callback: Callable[[Dict[int, float]], None]):
        """Start reading from serial port."""
        self.callback = callback
        try:
            self.ser = serial.Serial(
                self.port, self.baud, 
                timeout=self.timeout,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                parity="E"
            )
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            print(f"Serial adapter started on {self.port} at {self.baud} baud")
        except Exception as e:
            print(f"Failed to connect to serial port: {e}")
            raise
    
    def stop(self):
        """Stop reading from serial port."""
        self.running = False
        if self.ser:
            self.ser.close()
        if self.thread:
            self.thread.join(timeout=2.0)
    
    def is_running(self) -> bool:
        return self.running
    
    def _read_loop(self):
        """Main reading loop."""
        ranges = {}
        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    response = self.ser.read_all()
                    self.buffer.append(response)
                    
                    while self.buffer.size > 0:
                        msg = self.buffer.pop()
                        if msg is None:
                            continue
                        
                        message = Message(msg)
                        anchor_id = message.id
                        raw_val = message.data / 1000.0  # Convert mm to meters
                        
                        if anchor_id is not None:
                            ranges[anchor_id] = raw_val
                    
                    if ranges and self.callback:
                        self.callback(ranges.copy())
                        ranges.clear()
                
                time.sleep(0.01)  # Small delay to prevent CPU spinning
            except Exception as e:
                print(f"Error in serial read loop: {e}")
                time.sleep(0.1)


class MQTTInputAdapter(InputAdapter):
    """MQTT input adapter."""
    
    def __init__(self, broker: str, port: int = 1883, topic: str = "uwb/distances"):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = None
        self.running = False
        self.callback = None
    
    def start(self, callback: Callable[[Dict[int, float]], None]):
        """Start MQTT subscriber."""
        try:
            import paho.mqtt.client as mqtt
            self.callback = callback
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.connect(self.broker, self.port, 60)
            self.running = True
            self.client.loop_start()
            print(f"MQTT adapter started on {self.broker}:{self.port}, topic: {self.topic}")
        except ImportError:
            raise ImportError("paho-mqtt is required for MQTT adapter. Install with: pip install paho-mqtt")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def stop(self):
        """Stop MQTT subscriber."""
        self.running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
    
    def is_running(self) -> bool:
        return self.running
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        client.subscribe(self.topic)
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback."""
        try:
            data = json.loads(msg.payload.decode())
            # Expected format: {"anchor_id": distance, ...} or [{"id": anchor_id, "distance": dist}, ...]
            if isinstance(data, dict):
                distances = {int(k): float(v) for k, v in data.items()}
            elif isinstance(data, list):
                distances = {int(item["id"]): float(item["distance"]) for item in data}
            else:
                print(f"Unexpected MQTT message format: {data}")
                return
            
            if self.callback:
                self.callback(distances)
        except Exception as e:
            print(f"Error processing MQTT message: {e}")


class UDPInputAdapter(InputAdapter):
    """UDP input adapter."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5005):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.callback = None
        self.thread = None
    
    def start(self, callback: Callable[[Dict[int, float]], None]):
        """Start UDP listener."""
        self.callback = callback
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(1.0)
            self.running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            print(f"UDP adapter started on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to start UDP adapter: {e}")
            raise
    
    def stop(self):
        """Stop UDP listener."""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.thread:
            self.thread.join(timeout=2.0)
    
    def is_running(self) -> bool:
        return self.running
    
    def _read_loop(self):
        """Main reading loop."""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                try:
                    message = json.loads(data.decode())
                    # Expected format: {"anchor_id": distance, ...} or [{"id": anchor_id, "distance": dist}, ...]
                    if isinstance(message, dict):
                        distances = {int(k): float(v) for k, v in message.items()}
                    elif isinstance(message, list):
                        distances = {int(item["id"]): float(item["distance"]) for item in message}
                    else:
                        continue
                    
                    if self.callback:
                        self.callback(distances)
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON in UDP message: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error in UDP read loop: {e}")


class FileInputAdapter(InputAdapter):
    """File input adapter for reading from JSON file."""
    
    def __init__(self, filepath: str, poll_interval: float = 1.0):
        self.filepath = filepath
        self.poll_interval = poll_interval
        self.running = False
        self.callback = None
        self.thread = None
    
    def start(self, callback: Callable[[Dict[int, float]], None]):
        """Start reading from file."""
        self.callback = callback
        self.running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print(f"File adapter started reading from {self.filepath}")
    
    def stop(self):
        """Stop reading from file."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
    
    def is_running(self) -> bool:
        return self.running
    
    def _read_loop(self):
        """Main reading loop."""
        while self.running:
            try:
                with open(self.filepath, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        distances = {int(k): float(v) for k, v in data.items()}
                    elif isinstance(data, list):
                        distances = {int(item["id"]): float(item["distance"]) for item in data}
                    else:
                        continue
                    
                    if self.callback:
                        self.callback(distances)
            except FileNotFoundError:
                print(f"File not found: {self.filepath}")
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in file: {e}")
            except Exception as e:
                print(f"Error reading file: {e}")
            
            time.sleep(self.poll_interval)


# Helper classes from RTK-DW1000
class Message:
    """Message parser for serial protocol."""
    def __init__(self, data: bytes):
        self.id, self.data = struct.unpack('<BI', data)
    
    def __str__(self):
        return f"id: {self.id}, data: {self.data}"


class CircularBuffer:
    """Circular buffer for serial message parsing."""
    def __init__(self, size: int, element_size: int = 5):
        self.buffer = [b'\x00' for i in range(size)]
        self.head = 0
        self.size = 0
        self.tail = 0
        self.element_size = element_size

    def append(self, item: Optional[bytes]):
        if item is None:
            return
        items = item.split(b'\xff\xff\xff\x00')
        for item in items:
            if len(item) == 0:
                continue
            if len(item) > self.element_size:
                continue
            self.buffer[self.head] = item
            self.head = (self.head + 1) % len(self.buffer)
            self.size += 1
        if self.size > len(self.buffer):
            self.size = len(self.buffer)

    def pop(self) -> Optional[bytes]:
        if self.size == 0:
            return None
        item = self.buffer[self.tail]
        self.tail = (self.tail + 1) % len(self.buffer)
        self.size -= 1
        return item
