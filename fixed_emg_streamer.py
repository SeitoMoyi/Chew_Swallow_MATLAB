#!/usr/bin/env python3
"""
Fixed Real-Time EMG and Accelerometer Data Streaming with Delsys SDK
Python translation of MATLAB SMA_real_time_data_stream_plotting
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
    def __init__(self, host_ip='localhost', num_sensors=16):
        """
        Initialize the Delsys data streamer with configuration parameters.
        """
        # Configuration parameters
        self.HOST_IP = host_ip
        self.NUM_SENSORS = num_sensors
        
        # Muscle labels for each sensor channel
        self.muscle_labels = [
            'L-TIBI', 'L-GAST', 'L-RECT-DIST', 'L-RECT-PROX', 'L-VAST-LATE',
            'R-TIBI', 'R-GAST', 'R-RECT-DIST', 'R-RECT-PROX', 'R-VAST-LATE',
            'L-SEMI', 'R-SEMI', 'NC', 'NC', 'L-BICEP-FEMO', 'R-BICEP-FEMO'
        ]
        
        # Network connections
        self.comm_socket = None
        self.emg_socket = None
        self.acc_socket = None
        
        # Thread-safe queues
        self.emg_data_queue = queue.Queue(maxsize=1000)
        self.acc_data_queue = queue.Queue(maxsize=1000)
        
        # Circular buffers - initialize with default size
        self.buffer_size = 2000
        self.emg_buffers = [deque(maxlen=self.buffer_size) for _ in range(self.NUM_SENSORS)]
        self.acc_buffers = [deque(maxlen=self.buffer_size//14) for _ in range(self.NUM_SENSORS * 3)]
        
        # Threading control
        self.streaming = False
        self.threads = []
        
        # Sampling parameters
        self.emg_rate = 2000
        self.rate_adjusted_bytes = 1728
        
        # Plotting objects
        self.fig_emg = None
        self.fig_acc = None
        self.axes_emg = []
        self.axes_acc = []
        self.lines_emg = []
        self.lines_acc = []

    def setup_connections(self):
        """Establish TCP connections to Delsys system"""
        try:
            print("🔌 Establishing connections...")
            
            # Command connection
            self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.comm_socket.settimeout(10)  # 10 second timeout
            self.comm_socket.connect((self.HOST_IP, 50040))
            print("✅ Command connection established")
            
            # EMG data connection
            self.emg_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.emg_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.emg_socket.settimeout(10)
            self.emg_socket.connect((self.HOST_IP, 50041))
            print("✅ EMG connection established")
            
            # ACC data connection
            self.acc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.acc_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.acc_socket.settimeout(10)
            self.acc_socket.connect((self.HOST_IP, 50042))
            print("✅ ACC connection established")
            
            # Remove timeouts for data streaming
            self.emg_socket.settimeout(None)
            self.acc_socket.settimeout(None)
            
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
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"❌ Command error: {e}")
            return False

    def configure_system(self):
        """Configure the Delsys system sampling rate"""
        try:
            print("⚙️ Configuring system...")
            
            # Clear any existing data
            self.comm_socket.settimeout(0.1)
            try:
                while True:
                    self.comm_socket.recv(1024)
            except socket.timeout:
                pass
            self.comm_socket.settimeout(None)
            
            # Set sampling rate
            if not self.send_command("RATE 2000"):
                return False
            
            # Query actual rate
            if not self.send_command("RATE?"):
                return False
                
            try:
                response = self.comm_socket.recv(1024).decode().strip()
                print(f"📊 Sampling rate response: {response}")
                
                # Adjust parameters based on response
                if response == '1925.926':
                    self.rate_adjusted_bytes = 1664
                    actual_rate = 1925.926
                else:
                    self.rate_adjusted_bytes = 1728
                    actual_rate = 2000.0
                    
                # Update buffer size
                TARGET_TIME_WINDOW = 1.0
                self.buffer_size = int(actual_rate * TARGET_TIME_WINDOW)
                
                # Recreate buffers with correct size
                self.emg_buffers = [deque(maxlen=self.buffer_size) for _ in range(self.NUM_SENSORS)]
                self.acc_buffers = [deque(maxlen=self.buffer_size//14) for _ in range(self.NUM_SENSORS * 3)]
                
                print(f"✅ Buffer size: {self.buffer_size} samples")
                print(f"✅ Packet size: {self.rate_adjusted_bytes} bytes")
                return True
                
            except Exception as e:
                print(f"❌ Rate query error: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Configuration error: {e}")
            return False

    def setup_plots(self):
        """Create matplotlib figures and subplots"""
        print("📊 Setting up plots...")
        
        # Enable interactive mode
        plt.ion()
        
        # Setup EMG plots
        self.fig_emg, axes_emg_2d = plt.subplots(4, 4, figsize=(15, 10))
        self.fig_emg.suptitle('EMG Data', color='white', fontsize=16)
        self.fig_emg.patch.set_facecolor('black')
        
        self.axes_emg = axes_emg_2d.flatten()
        
        for i in range(self.NUM_SENSORS):
            ax = self.axes_emg[i]
            ax.set_facecolor([0.15, 0.15, 0.15])
            ax.grid(True, color=[0.9725, 0.9725, 0.9725], alpha=0.3)
            ax.tick_params(colors=[0.9725, 0.9725, 0.9725])
            ax.set_ylim([-0.005, 0.005])
            ax.set_xlim([0, self.buffer_size])
            
            # Create empty line
            line, = ax.plot([], [], 'y-', linewidth=1)
            self.lines_emg.append(line)
            
            # Labels
            if i % 4 == 0:
                ax.set_ylabel('V', color=[0.9725, 0.9725, 0.9725])
            else:
                ax.set_yticklabels([])
                
            if i >= 12:
                ax.set_xlabel('Samples', color=[0.9725, 0.9725, 0.9725])
            else:
                ax.set_xticklabels([])
            
            ax.set_title(f'EMG-{i+1} {self.muscle_labels[i]}', 
                        color=[0.9725, 0.9725, 0.9725], fontsize=10)

        # Setup ACC plots
        self.fig_acc, axes_acc_2d = plt.subplots(4, 4, figsize=(15, 10))
        self.fig_acc.suptitle('ACC Data', color='white', fontsize=16)
        self.fig_acc.patch.set_facecolor('black')
        
        self.axes_acc = axes_acc_2d.flatten()
        
        for i in range(self.NUM_SENSORS):
            ax = self.axes_acc[i]
            ax.set_facecolor([0.15, 0.15, 0.15])
            ax.grid(True, color=[0.9725, 0.9725, 0.9725], alpha=0.3)
            ax.tick_params(colors=[0.9725, 0.9725, 0.9725])
            ax.set_ylim([-8, 8])
            ax.set_xlim([0, self.buffer_size//14])
            
            # Create three lines for X, Y, Z
            line_x, = ax.plot([], [], 'r-', linewidth=1, label='X')
            line_y, = ax.plot([], [], 'b-', linewidth=1, label='Y')  
            line_z, = ax.plot([], [], 'g-', linewidth=1, label='Z')
            
            self.lines_acc.extend([line_x, line_y, line_z])
            
            # Labels
            if i % 4 == 0:
                ax.set_ylabel('g', color=[0.9725, 0.9725, 0.9725])
            else:
                ax.set_yticklabels([])
                
            if i >= 12:
                ax.set_xlabel('Samples', color=[0.9725, 0.9725, 0.9725])
            else:
                ax.set_xticklabels([])
            
            ax.set_title(f'ACC CH-{i+1}', color=[0.9725, 0.9725, 0.9725], fontsize=10)

        plt.tight_layout()
        print("✅ Plots created")

    def emg_data_thread(self):
        """Thread function for reading EMG data"""
        print("🔄 EMG data thread started")
        
        while self.streaming:
            try:
                # Read EMG data
                data_bytes = self.emg_socket.recv(self.rate_adjusted_bytes)
                
                if len(data_bytes) == self.rate_adjusted_bytes:
                    # Convert bytes to float32 array
                    samples = struct.unpack(f'{len(data_bytes)//4}f', data_bytes)
                    samples_array = np.array(samples)
                    
                    # Add to queue
                    try:
                        self.emg_data_queue.put_nowait(samples_array)
                    except queue.Full:
                        # Remove old data if queue is full
                        try:
                            self.emg_data_queue.get_nowait()
                            self.emg_data_queue.put_nowait(samples_array)
                        except queue.Empty:
                            pass
                        
            except socket.error as e:
                if self.streaming:
                    print(f"❌ EMG socket error: {e}")
                break
            except Exception as e:
                if self.streaming:
                    print(f"❌ EMG thread error: {e}")
                break
                
        print("🔄 EMG thread stopped")

    def acc_data_thread(self):
        """Thread function for reading ACC data"""
        print("🔄 ACC data thread started")
        
        while self.streaming:
            try:
                # Read ACC data
                data_bytes = self.acc_socket.recv(384)
                
                if len(data_bytes) == 384:
                    # Convert bytes to float32 array
                    samples = struct.unpack(f'{len(data_bytes)//4}f', data_bytes)
                    samples_array = np.array(samples)
                    
                    # Add to queue
                    try:
                        self.acc_data_queue.put_nowait(samples_array)
                    except queue.Full:
                        # Remove old data if queue is full
                        try:
                            self.acc_data_queue.get_nowait()
                            self.acc_data_queue.put_nowait(samples_array)
                        except queue.Empty:
                            pass
                        
            except socket.error as e:
                if self.streaming:
                    print(f"❌ ACC socket error: {e}")
                break
            except Exception as e:
                if self.streaming:
                    print(f"❌ ACC thread error: {e}")
                break
                
        print("🔄 ACC thread stopped")

    def data_processing_thread(self):
        """Thread to process queued data and update buffers"""
        print("🔄 Data processing thread started")
        
        while self.streaming:
            try:
                # Process EMG data
                try:
                    emg_data = self.emg_data_queue.get_nowait()
                    # Demultiplex data
                    for channel in range(self.NUM_SENSORS):
                        channel_data = emg_data[channel::16]
                        self.emg_buffers[channel].extend(channel_data)
                        
                except queue.Empty:
                    pass
                
                # Process ACC data
                try:
                    acc_data = self.acc_data_queue.get_nowait()
                    # Demultiplex ACC data
                    for axis in range(48):
                        axis_data = acc_data[axis::48]
                        if axis < len(self.acc_buffers):
                            self.acc_buffers[axis].extend(axis_data)
                        
                except queue.Empty:
                    pass
                    
                time.sleep(0.001)
                
            except Exception as e:
                if self.streaming:
                    print(f"❌ Processing thread error: {e}")
                break
                
        print("🔄 Processing thread stopped")

    def update_plots(self, frame):
        """Animation function to update plots"""
        try:
            # Update EMG plots
            for i in range(self.NUM_SENSORS):
                if len(self.emg_buffers[i]) > 0:
                    y_data = list(self.emg_buffers[i])
                    x_data = list(range(len(y_data)))
                    self.lines_emg[i].set_data(x_data, y_data)
            
            # Update ACC plots
            for i in range(self.NUM_SENSORS):
                for axis in range(3):
                    line_idx = i * 3 + axis
                    buffer_idx = i * 3 + axis
                    
                    if (line_idx < len(self.lines_acc) and 
                        buffer_idx < len(self.acc_buffers) and 
                        len(self.acc_buffers[buffer_idx]) > 0):
                        
                        y_data = list(self.acc_buffers[buffer_idx])
                        x_data = list(range(len(y_data)))
                        self.lines_acc[line_idx].set_data(x_data, y_data)

        except Exception as e:
            print(f"❌ Plot update error: {e}")

        return self.lines_emg + self.lines_acc

    def start_streaming(self):
        """Start data acquisition and plotting"""
        print("🚀 Starting streaming...")
        
        if not self.setup_connections():
            return False
            
        if not self.configure_system():
            return False
            
        # Send START command
        if not self.send_command("START"):
            return False
        print("▶️ START command sent")
        
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
        
        print("🔄 Starting data threads...")
        for thread in self.threads:
            thread.start()
        
        # Start animations
        print("🎬 Starting animations...")
        self.ani_emg = FuncAnimation(self.fig_emg, self.update_plots, 
                                    interval=100, blit=False, cache_frame_data=False)
        self.ani_acc = FuncAnimation(self.fig_acc, self.update_plots, 
                                    interval=100, blit=False, cache_frame_data=False)
        
        # Show plots
        print("📊 Displaying plots...")
        plt.show(block=True)  # Block until windows are closed
        
        return True

    def stop_streaming(self):
        """Stop data acquisition"""
        print("🛑 Stopping streaming...")
        self.streaming = False
        
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        
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
    
    # Configuration
    HOST_IP = 'localhost'  # Using localhost since simulator is local
    NUM_SENSORS = 16
    
    # Create streamer object
    streamer = DelsysStreamer(host_ip=HOST_IP, num_sensors=NUM_SENSORS)
    
    print("🔌 Starting Delsys EMG/ACC Streamer...")
    print("📡 Connecting to simulator...")
    print("⚠️  Press Ctrl+C to stop")
    
    try:
        if streamer.start_streaming():
            print("✅ Streaming completed")
        else:
            print("❌ Failed to start streaming")
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()