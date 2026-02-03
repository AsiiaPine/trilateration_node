"""
Output adapters for sending position data to various destinations.
"""
import json
import socket
import time
from typing import Tuple, Optional, Dict, Any
from abc import ABC, abstractmethod


class OutputAdapter(ABC):
    """Base class for output adapters."""
    
    @abstractmethod
    def send_position(self, position: Tuple[float, float, float], timestamp: Optional[float] = None):
        """Send position data."""
        pass
    
    @abstractmethod
    def close(self):
        """Close the adapter."""
        pass


class MavlinkOutputAdapter(OutputAdapter):
    """MAVLink output adapter using pymavlink."""
    
    def __init__(self, connection_string: str = "udp:127.0.0.1:14550", 
                 system_id: int = 1, component_id: int = 1):
        """
        Initialize MAVLink adapter.
        
        :param connection_string: MAVLink connection string (e.g., "udp:127.0.0.1:14550", "tcp:127.0.0.1:5760")
        :param system_id: MAVLink system ID
        :param component_id: MAVLink component ID
        """
        self.connection_string = connection_string
        self.system_id = system_id
        self.component_id = component_id
        self.connection = None
        self.mav = None
        self._initialize()
    
    def _initialize(self):
        """Initialize MAVLink connection."""
        try:
            from pymavlink import mavutil
            self.connection = mavutil.mavlink_connection(self.connection_string)
            self.mav = self.connection.mav
            print(f"MAVLink adapter initialized: {self.connection_string}")
        except ImportError:
            raise ImportError("pymavlink is required for MAVLink adapter. Install with: pip install pymavlink")
        except Exception as e:
            print(f"Failed to initialize MAVLink connection: {e}")
            raise
    
    def send_position(self, position: Tuple[float, float, float], timestamp: Optional[float] = None):
        """Send position via MAVLink LOCAL_POSITION_NED message."""
        if self.mav is None:
            return
        
        x, y, z = position
        timestamp_ms = int((timestamp or time.time()) * 1000) if timestamp else 0
        
        try:
            # Send LOCAL_POSITION_NED message
            self.mav.local_position_ned_send(
                timestamp_ms,
                x,  # x position (m)
                y,  # y position (m)
                z,  # z position (m)
                0,  # vx velocity (m/s)
                0,  # vy velocity (m/s)
                0   # vz velocity (m/s)
            )
        except Exception as e:
            print(f"Error sending MAVLink message: {e}")
    
    def close(self):
        """Close MAVLink connection."""
        if self.connection:
            self.connection.close()


class MavrosOutputAdapter(OutputAdapter):
    """MAVROS output adapter (ROS2)."""
    
    def __init__(self, topic_prefix: str = "mavros", frame_id: str = "map"):
        """
        Initialize MAVROS adapter.
        
        :param topic_prefix: ROS2 topic prefix (default: "mavros")
        :param frame_id: Frame ID for messages
        """
        self.topic_prefix = topic_prefix
        self.frame_id = frame_id
        self.publisher = None
        self.node = None
        self._initialize()
    
    def _initialize(self):
        """Initialize ROS2 node and publisher."""
        try:
            import rclpy
            from geometry_msgs.msg import PoseStamped
            
            if not rclpy.ok():
                rclpy.init()
            
            from rclpy.node import Node
            self.node = Node('uwb_localizer_output')
            self.PoseStamped = PoseStamped
            
            topic = f"{self.topic_prefix}/fake_gps/mocap/pose"
            self.publisher = self.node.create_publisher(PoseStamped, topic, 10)
            print(f"MAVROS adapter initialized: {topic}")
        except ImportError:
            raise ImportError("rclpy is required for MAVROS adapter. Install ROS2 dependencies.")
        except Exception as e:
            print(f"Failed to initialize MAVROS adapter: {e}")
            raise
    
    def send_position(self, position: Tuple[float, float, float], timestamp: Optional[float] = None):
        """Send position via ROS2 PoseStamped message."""
        if self.publisher is None:
            return
        
        x, y, z = position
        
        try:
            pose = self.PoseStamped()
            if self.node:
                pose.header.stamp = self.node.get_clock().now().to_msg()
            pose.header.frame_id = self.frame_id
            pose.pose.position.x = x
            pose.pose.position.y = y
            pose.pose.position.z = z
            pose.pose.orientation.w = 1.0
            
            self.publisher.publish(pose)
            
            # Spin once to process callbacks
            if self.node:
                import rclpy
                rclpy.spin_once(self.node, timeout_sec=0.01)
        except Exception as e:
            print(f"Error sending MAVROS message: {e}")
    
    def close(self):
        """Close ROS2 node."""
        if self.node:
            try:
                import rclpy
                rclpy.shutdown()
            except:
                pass


class UDPOutputAdapter(OutputAdapter):
    """UDP output adapter."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5006):
        """
        Initialize UDP adapter.
        
        :param host: Target host
        :param port: Target port
        """
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"UDP output adapter initialized: {host}:{port}")
    
    def send_position(self, position: Tuple[float, float, float], timestamp: Optional[float] = None):
        """Send position via UDP as JSON."""
        x, y, z = position
        message = {
            "position": {"x": x, "y": y, "z": z},
            "timestamp": timestamp or time.time()
        }
        
        try:
            data = json.dumps(message).encode()
            self.socket.sendto(data, (self.host, self.port))
        except Exception as e:
            print(f"Error sending UDP message: {e}")
    
    def close(self):
        """Close UDP socket."""
        if self.socket:
            self.socket.close()


class FileOutputAdapter(OutputAdapter):
    """File output adapter for logging positions."""
    
    def __init__(self, filepath: str, mode: str = "a"):
        """
        Initialize file adapter.
        
        :param filepath: Path to output file
        :param mode: File mode ('a' for append, 'w' for write)
        """
        self.filepath = filepath
        self.mode = mode
        self.file = open(filepath, mode)
        print(f"File output adapter initialized: {filepath}")
    
    def send_position(self, position: Tuple[float, float, float], timestamp: Optional[float] = None):
        """Write position to file as JSON line."""
        x, y, z = position
        message = {
            "position": {"x": x, "y": y, "z": z},
            "timestamp": timestamp or time.time()
        }
        
        try:
            self.file.write(json.dumps(message) + "\n")
            self.file.flush()
        except Exception as e:
            print(f"Error writing to file: {e}")
    
    def close(self):
        """Close file."""
        if self.file:
            self.file.close()


class ConsoleOutputAdapter(OutputAdapter):
    """Console output adapter for debugging."""
    
    def __init__(self, format: str = "json"):
        """
        Initialize console adapter.
        
        :param format: Output format ('json' or 'human')
        """
        self.format = format
        print("Console output adapter initialized")
    
    def send_position(self, position: Tuple[float, float, float], timestamp: Optional[float] = None):
        """Print position to console."""
        x, y, z = position
        if self.format == "json":
            message = {
                "position": {"x": x, "y": y, "z": z},
                "timestamp": timestamp or time.time()
            }
            print(json.dumps(message))
        else:
            print(f"Position: x={x:.3f}, y={y:.3f}, z={z:.3f}")
    
    def close(self):
        """Nothing to close for console output."""
        pass


class MultiOutputAdapter(OutputAdapter):
    """Adapter that sends to multiple output adapters."""
    
    def __init__(self, adapters: list):
        """
        Initialize multi-output adapter.
        
        :param adapters: List of output adapters
        """
        self.adapters = adapters
        print(f"Multi-output adapter initialized with {len(adapters)} adapters")
    
    def send_position(self, position: Tuple[float, float, float], timestamp: Optional[float] = None):
        """Send position to all adapters."""
        for adapter in self.adapters:
            try:
                adapter.send_position(position, timestamp)
            except Exception as e:
                print(f"Error in adapter {type(adapter).__name__}: {e}")
    
    def close(self):
        """Close all adapters."""
        for adapter in self.adapters:
            try:
                adapter.close()
            except Exception as e:
                print(f"Error closing adapter {type(adapter).__name__}: {e}")
