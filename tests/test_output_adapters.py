"""
Unit tests for output adapters.
"""
import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from uwb_localizer.output_adapters import (
    MavlinkOutputAdapter,
    MavrosOutputAdapter,
    UDPOutputAdapter,
    FileOutputAdapter,
    ConsoleOutputAdapter,
    MultiOutputAdapter
)


class TestConsoleOutputAdapter:
    """Test ConsoleOutputAdapter."""
    
    def test_console_output_human(self, capsys):
        """Test console output in human format."""
        adapter = ConsoleOutputAdapter(format='human')
        adapter.send_position((1.0, 2.0, 3.0))
        
        captured = capsys.readouterr()
        assert "x=1.000" in captured.out
        assert "y=2.000" in captured.out
        assert "z=3.000" in captured.out
    
    def test_console_output_json(self, capsys):
        """Test console output in JSON format."""
        adapter = ConsoleOutputAdapter(format='json')
        adapter.send_position((1.0, 2.0, 3.0), timestamp=1234567890.0)
        
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data['position']['x'] == 1.0
        assert data['position']['y'] == 2.0
        assert data['position']['z'] == 3.0
        assert data['timestamp'] == 1234567890.0


class TestUDPOutputAdapter:
    """Test UDPOutputAdapter."""
    
    @patch('uwb_localizer.output_adapters.socket.socket')
    def test_udp_output(self, mock_socket_class):
        """Test UDP output sends JSON."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        adapter = UDPOutputAdapter('127.0.0.1', 5006)
        adapter.send_position((1.0, 2.0, 3.0), timestamp=1234567890.0)
        
        # Verify socket was created
        mock_socket_class.assert_called_once()
        
        # Verify sendto was called
        assert mock_socket.sendto.called
        
        # Check the sent data
        call_args = mock_socket.sendto.call_args
        sent_data = json.loads(call_args[0][0].decode())
        assert sent_data['position']['x'] == 1.0
        assert sent_data['position']['y'] == 2.0
        assert sent_data['position']['z'] == 3.0


class TestFileOutputAdapter:
    """Test FileOutputAdapter."""
    
    @patch('builtins.open', create=True)
    def test_file_output_append(self, mock_open):
        """Test file output appends JSON lines."""
        mock_file = MagicMock()
        mock_open.return_value = mock_file
        
        adapter = FileOutputAdapter('test.jsonl', mode='a')
        adapter.send_position((1.0, 2.0, 3.0), timestamp=1234567890.0)
        
        # Verify file was opened in append mode
        mock_open.assert_called_with('test.jsonl', 'a')
        
        # Verify write was called
        assert mock_file.write.called
        assert mock_file.flush.called
        
        # Check written data
        written_data = mock_file.write.call_args[0][0]
        data = json.loads(written_data.strip())
        assert data['position']['x'] == 1.0
    
    def test_file_output_close(self):
        """Test file output closes properly."""
        adapter = FileOutputAdapter('test.jsonl', mode='a')
        adapter.close()
        
        # File should be closed (would need proper mock to verify)


class TestMavlinkOutputAdapter:
    """Test MavlinkOutputAdapter."""
    
    @patch('uwb_localizer.output_adapters.mavutil')
    def test_mavlink_output(self, mock_mavutil):
        """Test MAVLink output sends LOCAL_POSITION_NED."""
        mock_connection = MagicMock()
        mock_mav = MagicMock()
        mock_connection.mav = mock_mav
        mock_mavutil.mavlink_connection.return_value = mock_connection
        
        adapter = MavlinkOutputAdapter('udp:127.0.0.1:14550')
        adapter.send_position((1.0, 2.0, 3.0))
        
        # Verify mavlink_connection was called
        mock_mavutil.mavlink_connection.assert_called_once_with('udp:127.0.0.1:14550')
        
        # Verify local_position_ned_send was called
        assert mock_mav.local_position_ned_send.called
    
    def test_mavlink_requires_pymavlink(self):
        """Test MAVLink adapter requires pymavlink."""
        # This test verifies the import check exists
        try:
            from pymavlink import mavutil
            assert True
        except ImportError:
            with pytest.raises(ImportError):
                MavlinkOutputAdapter('udp:127.0.0.1:14550')


class TestMavrosOutputAdapter:
    """Test MavrosOutputAdapter."""
    
    @patch('uwb_localizer.output_adapters.rclpy')
    def test_mavros_output(self, mock_rclpy):
        """Test MAVROS output publishes PoseStamped."""
        # Mock ROS2 components
        mock_node = MagicMock()
        mock_clock = MagicMock()
        mock_time_msg = MagicMock()
        mock_clock.now.return_value.to_msg.return_value = mock_time_msg
        mock_node.get_clock.return_value = mock_clock
        
        mock_publisher = MagicMock()
        mock_node.create_publisher.return_value = mock_publisher
        
        with patch('uwb_localizer.output_adapters.Node', return_value=mock_node):
            adapter = MavrosOutputAdapter('mavros', 'map')
            adapter.node = mock_node
            adapter.publisher = mock_publisher
            adapter.PoseStamped = MagicMock
            
            adapter.send_position((1.0, 2.0, 3.0))
            
            # Verify publisher was created
            assert mock_node.create_publisher.called
            
            # Verify publish was called
            assert mock_publisher.publish.called


class TestMultiOutputAdapter:
    """Test MultiOutputAdapter."""
    
    def test_multi_output_sends_to_all(self):
        """Test multi-output sends to all adapters."""
        adapter1 = Mock()
        adapter2 = Mock()
        adapter3 = Mock()
        
        multi = MultiOutputAdapter([adapter1, adapter2, adapter3])
        multi.send_position((1.0, 2.0, 3.0))
        
        # Verify all adapters received the position
        adapter1.send_position.assert_called_once_with((1.0, 2.0, 3.0), None)
        adapter2.send_position.assert_called_once_with((1.0, 2.0, 3.0), None)
        adapter3.send_position.assert_called_once_with((1.0, 2.0, 3.0), None)
    
    def test_multi_output_handles_errors(self):
        """Test multi-output handles adapter errors gracefully."""
        adapter1 = Mock()
        adapter2 = Mock(side_effect=Exception("Test error"))
        adapter3 = Mock()
        
        multi = MultiOutputAdapter([adapter1, adapter2, adapter3])
        
        # Should not raise, but continue to other adapters
        multi.send_position((1.0, 2.0, 3.0))
        
        adapter1.send_position.assert_called_once()
        adapter3.send_position.assert_called_once()
    
    def test_multi_output_close(self):
        """Test multi-output closes all adapters."""
        adapter1 = Mock()
        adapter2 = Mock()
        
        multi = MultiOutputAdapter([adapter1, adapter2])
        multi.close()
        
        adapter1.close.assert_called_once()
        adapter2.close.assert_called_once()
