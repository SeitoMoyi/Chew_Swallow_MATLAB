#!/usr/bin/env python3
"""
Real-Time EMG and Accelerometer Data Streaming with Delsys SDK
Python translation of MATLAB SMA_real_time_data_stream_plotting
Author: [Your Name]
"""

import socket
import struct
import threading
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import queue
import signal
import sys

class DelsysStreamer:
    def __init__(self, host_ip='192.168.3.222', num_sensors=16):
        # Configuration
        self.HOST_IP = host_ip
        self.NUM_SENSORS = num_sensors
        
        # Muscle labels - update to match your setup
        self.muscle_labels = [
            'L-TIBI', 'L-GAST', 'L-RECT-DIST', 'L-RECT-PROX', 'L-VAST-LATE',
            'R-TIBI', 'R-GAST', 'R-RECT-DIST', 'R-RECT-PROX', 'R-VAST-LATE',
            'L-SEMI', 'R-SEMI', 'NC', 'NC', 'L-BICEP-FEMO', 'R-BICEP-FEMO'
        ]
        
        # Network connections
        self.comm_socket = None      # Port 50040 - Commands
        self.emg_socket = None       # Port 50041 - EMG data
        self.acc_socket = None       # Port 50042 - ACC data
        
        # Data storage - thread-safe queues
        self.emg_data_queue = queue.Queue(maxsize=10000)
        self.acc_data_queue = queue.Queue(maxsize=10000)
        
        # Circular buffers for plotting (similar to MATLAB's data_array)
        self.buffer_size = 2000  # samples to display
        self.emg_buffers = [deque(maxlen=self.buffer_size) for _ in range(self.NUM_SENSORS)]
        self.acc_buffers = [deque(maxlen=self.buffer_size//14) for _ in range(self.NUM_SENSORS * 3)]
        
        # Threading control
        self.streaming = False
        self.threads = []
        
        # Sampling parameters
        self.emg_rate = 2000
        self.rate_adjusted_bytes = 1728  # Will be determined dynamically
        
        # Plotting
        self.fig_emg = None
        self.fig_acc = None
        self.axes_emg = []
        self.axes_acc = []
        self.lines_emg = []
        self.lines_acc = []

    def setup_connections(self):
        """Establish TCP connections to Delsys system"""
        try:
            # Command connection
            self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.comm_socket.connect((self.HOST_IP, 50040))
            
            # EMG data connection
            self.emg_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.emg_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.emg_socket.connect((self.HOST_IP, 50041))
            
            # ACC data connection
            self.acc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.acc_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.acc_socket.connect((self.HOST_IP, 50042))
            
            print("✅ All connections established successfully")
            return True
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.cleanup_connections()
            return False

    def setup_connections(self):
        """Establish TCP connections to Delsys system"""
        try:
            # Command connection
            self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.comm_socket.connect((self.HOST_IP, 50040))
            
            # EMG data connection
            self.emg_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.emg_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.emg_socket.connect((self.HOST_IP, 50041))
            
            # ACC data connection
            self.acc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.acc_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.acc_socket.connect((self.HOST_IP, 50042))
            
            print("✅ All connections established successfully")
            return True
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.cleanup_connections()
            return False

    def send_command(self, command):
        """Send command to Delsys system"""
        try:
            cmd_bytes = f"{command}\r\n\r".encode()
            self.comm_socket.send(cmd_bytes)
            time.sleep(0.1)  # Brief pause like MATLAB's pause(1)
            return True
        except Exception as e:
            print(f"Command error: {e}")
            return False

    def configure_system(self):
        """Configure sampling rate and determine buffer parameters"""
        try:
            # Clear any existing data
            self.comm_socket.settimeout(0.1)
            try:
                while True:
                    self.comm_socket.recv(1024)
            except socket.timeout:
                pass
            self.comm_socket.settimeout(None)
            
            # Set sampling rate
            self.send_command("RATE 2000")
            
            # Query actual rate
            self.send_command("RATE?")
            response = self.comm_socket.recv(1024).decode().strip()
            
            print(f"Sampling rate response: {response}")
            
            # Adjust buffer size based on actual rate (like MATLAB logic)
            if response == '1925.926':
                self.rate_adjusted_bytes = 1664
            else:
                self.rate_adjusted_bytes = 1728
                
            print(f"Using buffer size: {self.rate_adjusted_bytes} bytes")
            return True
            
        except Exception as e:
            print(f"Configuration error: {e}")
            return False

    def setup_plots(self):
        """Create matplotlib figures and subplots"""
        # Setup EMG plots (4x4 grid)
        self.fig_emg, axes_emg_2d = plt.subplots(4, 4, figsize=(15, 10))
        self.fig_emg.suptitle('EMG Data', color='white')
        self.fig_emg.patch.set_facecolor('black')
        
        self.axes_emg = axes_emg_2d.flatten()
        
        for i in range(self.NUM_SENSORS):
            ax = self.axes_emg[i]
            ax.set_facecolor([0.15, 0.15, 0.15])
            ax.grid(True, color=[0.9725, 0.9725, 0.9725])
            ax.tick_params(colors=[0.9725, 0.9725, 0.9725])
            ax.set_ylim([-0.005, 0.005])
            ax.set_xlim([0, self.buffer_size])
            
            # Create empty line
            line, = ax.plot([], [], 'y-', linewidth=1)
            self.lines_emg.append(line)
            
            # Labels and titles
            if i % 4 == 0:
                ax.set_ylabel('V', color=[0.9725, 0.9725, 0.9725])
            if i >= 12:
                ax.set_xlabel('Samples', color=[0.9725, 0.9725, 0.9725])
            
            ax.set_title(f'EMG-{i+1} {self.muscle_labels[i]}', 
                        color=[0.9725, 0.9725, 0.9725])

        # Setup ACC plots (4x4 grid, 3 lines each)
        self.fig_acc, axes_acc_2d = plt.subplots(4, 4, figsize=(15, 10))
        self.fig_acc.suptitle('ACC Data', color='white')
        self.fig_acc.patch.set_facecolor('black')
        
        self.axes_acc = axes_acc_2d.flatten()
        
        for i in range(self.NUM_SENSORS):
            ax = self.axes_acc[i]
            ax.set_facecolor([0.15, 0.15, 0.15])
            ax.grid(True, color=[0.9725, 0.9725, 0.9725])
            ax.tick_params(colors=[0.9725, 0.9725, 0.9725])
            ax.set_ylim([-8, 8])
            ax.set_xlim([0, self.buffer_size//14])
            
            # Create 3 lines for X, Y, Z axes
            line_x, = ax.plot([], [], 'r-', linewidth=1)  # X - Red
            line_y, = ax.plot([], [], 'b-', linewidth=1)  # Y - Blue  
            line_z, = ax.plot([], [], 'g-', linewidth=1)  # Z - Green
            
            self.lines_acc.extend([line_x, line_y, line_z])
            
            # Labels
            if i % 4 == 0:
                ax.set_ylabel('g', color=[0.9725, 0.9725, 0.9725])
            if i >= 12:
                ax.set_xlabel('Samples', color=[0.9725, 0.9725, 0.9725])
            
            ax.set_title(f'ACC CH-{i+1}', color=[0.9725, 0.9725, 0.9725])

        plt.tight_layout()

    def emg_data_thread(self):
        """Thread function for reading EMG data"""
        print("🔄 EMG data thread started")
        
        while self.streaming:
            try:
                # Read data in chunks (similar to MATLAB's BytesAvailableFcn)
                data_bytes = self.emg_socket.recv(self.rate_adjusted_bytes)
                
                if len(data_bytes) == self.rate_adjusted_bytes:
                    # Convert bytes to float32 array (similar to MATLAB's typecast)
                    samples = struct.unpack(f'{len(data_bytes)//4}f', data_bytes)
                    samples_array = np.array(samples)
                    
                    # Add to queue for processing
                    try:
                        self.emg_data_queue.put_nowait(samples_array)
                    except queue.Full:
                        print("⚠️ EMG queue full, dropping data")
                        
            except Exception as e:
                if self.streaming:
                    print(f"EMG thread error: {e}")
                break

    def acc_data_thread(self):
        """Thread function for reading ACC data"""
        print("🔄 ACC data thread started")
        
        while self.streaming:
            try:
                # Read ACC data in chunks
                data_bytes = self.acc_socket.recv(384)  # 384 bytes as in MATLAB
                
                if len(data_bytes) == 384:
                    # Convert bytes to float32 array
                    samples = struct.unpack(f'{len(data_bytes)//4}f', data_bytes)
                    samples_array = np.array(samples)
                    
                    # Add to queue
                    try:
                        self.acc_data_queue.put_nowait(samples_array)
                    except queue.Full:
                        print("⚠️ ACC queue full, dropping data")
                        
            except Exception as e:
                if self.streaming:
                    print(f"ACC thread error: {e}")
                break

    def data_processing_thread(self):
        """Thread to process queued data and update buffers"""
        print("🔄 Data processing thread started")
        
        while self.streaming:
            try:
                # Process EMG data
                try:
                    emg_data = self.emg_data_queue.get_nowait()
                    # Demultiplex data (extract every 16th sample for each channel)
                    for channel in range(self.NUM_SENSORS):
                        channel_data = emg_data[channel::16]  # Every 16th sample
                        self.emg_buffers[channel].extend(channel_data)
                        
                except queue.Empty:
                    pass
                
                # Process ACC data  
                try:
                    acc_data = self.acc_data_queue.get_nowait()
                    # Demultiplex ACC data (48 channels = 16 sensors × 3 axes)
                    for axis in range(48):
                        axis_data = acc_data[axis::48]  # Every 48th sample
                        self.acc_buffers[axis].extend(axis_data)
                        
                except queue.Empty:
                    pass
                    
                time.sleep(0.001)  # Small delay to prevent excessive CPU usage
                
            except Exception as e:
                print(f"Processing thread error: {e}")

    def update_plots(self, frame):
        """Animation function to update plots"""
        # Update EMG plots
        for i in range(self.NUM_SENSORS):
            if len(self.emg_buffers[i]) > 0:
                y_data = list(self.emg_buffers[i])
                x_data = list(range(len(y_data)))
                self.lines_emg[i].set_data(x_data, y_data)
        
        # Update ACC plots (3 lines per sensor)
        for i in range(self.NUM_SENSORS):
            for axis in range(3):
                line_idx = i * 3 + axis
                buffer_idx = i * 3 + axis
                
                if buffer_idx < len(self.acc_buffers) and len(self.acc_buffers[buffer_idx]) > 0:
                    y_data = list(self.acc_buffers[buffer_idx])
                    x_data = list(range(len(y_data)))
                    self.lines_acc[line_idx].set_data(x_data, y_data)

        return self.lines_emg + self.lines_acc

    def start_streaming(self):
        """Start data acquisition and plotting"""
        if not self.setup_connections():
            return False
            
        if not self.configure_system():
            return False
            
        # Send START command
        self.send_command("START")
        print("🚀 Streaming started")
        
        # Setup plots
        self.setup_plots()
        
        # Start streaming
        self.streaming = True
        
        # Start data threads
        self.threads = [
            threading.Thread(target=self.emg_data_thread, daemon=True),
            threading.Thread(target=self.acc_data_thread, daemon=True),
            threading.Thread(target=self.data_processing_thread, daemon=True)
        ]
        
        for thread in self.threads:
            thread.start()
        
        # Start animation
        self.ani_emg = FuncAnimation(self.fig_emg, self.update_plots, 
                                    interval=100, blit=False, cache_frame_data=False)
        self.ani_acc = FuncAnimation(self.fig_acc, self.update_plots, 
                                    interval=100, blit=False, cache_frame_data=False)
        
        # Show plots
        plt.show()
        
        return True

    def stop_streaming(self):
        """Stop data acquisition"""
        print("🛑 Stopping streaming...")
        self.streaming = False
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
        
        self.cleanup_connections()

    def cleanup_connections(self):
        """Close all network connections"""
        for sock, name in [(self.comm_socket, "Command"), 
                          (self.emg_socket, "EMG"), 
                          (self.acc_socket, "ACC")]:
            if sock:
                try:
                    sock.close()
                    print(f"✅ {name} connection closed")
                except:
                    pass

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Shutting down...")
    if 'streamer' in globals():
        streamer.stop_streaming()
    sys.exit(0)

def main():
    """Main function"""
    global streamer
    
    # Setup signal handling
    signal.signal(signal.SIGINT, signal_handler)
    
    # Configuration - CHANGE THESE FOR YOUR SETUP
    HOST_IP = '192.168.3.222'  # Update to your Delsys system IP
    NUM_SENSORS = 16           # Update to match your sensor count
    
    # Create streamer object
    streamer = DelsysStreamer(host_ip=HOST_IP, num_sensors=NUM_SENSORS)
    
    print("🔌 Starting Delsys EMG/ACC Streamer...")
    print("📡 Make sure Trigno Control Utility is running!")
    print("⚠️  Press Ctrl+C to stop")
    
    try:
        if streamer.start_streaming():
            print("✅ Streaming active - close plot windows to exit")
        else:
            print("❌ Failed to start streaming")
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()