#!/usr/bin/env python3
"""
Real-Time EMG Data Streaming with Delsys SDK
Processes EMG signals with:
    1. DC offset removal
    2. Notch filter (60 Hz powerline interference)
    3. Band-pass filter (20-450 Hz for EMG frequency range)
    4. Full-wave rectification
    5. Envelope extraction via low-pass filtering
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
from scipy.signal import butter, lfilter, filtfilt, iirnotch

class DelsysStreamer:
    def __init__(self, host_ip='localhost', num_sensors=16, sampling_rate=2000.0):
        """
        Initialize the Delsys data streamer with configuration parameters.
        """
        # Configuration parameters
        self.HOST_IP = host_ip
        self.NUM_SENSORS = num_sensors
        self.SAMPLING_RATE = sampling_rate
        
        # Muscle labels for each sensor channel
        self.muscle_labels = [
            'L-TIBI', 'L-GAST', 'L-RECT-DIST', 'L-RECT-PROX', 'L-VAST-LATE',
            'R-TIBI', 'R-GAST', 'R-RECT-DIST', 'R-RECT-PROX', 'R-VAST-LATE',
            'L-SEMI', 'R-SEMI', 'NC', 'NC', 'L-BICEP-FEMO', 'R-BICEP-FEMO'
        ]
        
        # Network connections
        self.comm_socket = None
        self.emg_socket = None

        # Thread-safe queues
        self.emg_data_queue = queue.Queue(maxsize=1000)

        # Circular buffers for processed EMG data
        self.buffer_size = int(self.SAMPLING_RATE * 1.0)  # 1 second buffer
        self.emg_buffers = [deque(maxlen=self.buffer_size) for _ in range(self.NUM_SENSORS)]

        # Buffers to accumulate samples before applying filters
        self.ACCUMULATION_SIZE = 75
        self.emg_processing_buffers = [deque(maxlen=self.ACCUMULATION_SIZE) for _ in range(self.NUM_SENSORS)]

        # Threading control
        self.streaming = False
        self.threads = []

        # Sampling parameters
        self.emg_rate = self.SAMPLING_RATE
        self.rate_adjusted_bytes = 1728  # Will be updated by configure_system

        # Plotting objects
        self.fig_emg = None
        self.axes_emg = []
        self.lines_emg = []

        # Pre-calculate filter coefficients
        self._design_filters()

    def _design_filters(self):
        """Pre-calculate filter coefficients for efficiency."""
        fs = self.SAMPLING_RATE
        # 1. DC Offset Removal (High-pass)
        hp_cutoff = 0.5
        hp_order = 2
        self.hp_b, self.hp_a = butter(hp_order, hp_cutoff / (0.5 * fs), btype='high')

        # 2. Notch Filter (60 Hz)
        notch_freq = 60.0
        quality_factor = 30.0
        self.notch_b, self.notch_a = iirnotch(notch_freq / (0.5 * fs), quality_factor)

        # 3. Band-pass Filter (20-450 Hz)
        bp_low = 20.0
        bp_high = 450.0
        bp_order = 4
        self.bp_b, self.bp_a = butter(bp_order, [bp_low / (0.5 * fs), bp_high / (0.5 * fs)], btype='band')

        # 4. Envelope Extraction (Low-pass after rectification)
        lp_cutoff = 10.0
        lp_order = 2
        self.lp_b, self.lp_a = butter(lp_order, lp_cutoff / (0.5 * fs), btype='low')
        print("✅ Filter coefficients designed.")

    def process_emg_channel(self, data):
        """
        Apply the sequence of signal processing steps to a single EMG channel.
        Assumes data is a 1D numpy array.
        """
        # Make a copy to avoid modifying the original data
        processed_data = np.copy(data)

        # 1. DC offset removal (High-pass filter)
        processed_data = filtfilt(self.hp_b, self.hp_a, processed_data)

        # 2. Notch filter (60 Hz powerline interference)
        processed_data = filtfilt(self.notch_b, self.notch_a, processed_data)

        # 3. Band-pass filter (20-450 Hz for EMG frequency range)
        processed_data = filtfilt(self.bp_b, self.bp_a, processed_data)

        # 4. Full-wave rectification
        processed_data = np.abs(processed_data)

        # 5. Envelope extraction via low-pass filtering
        processed_data = filtfilt(self.lp_b, self.lp_a, processed_data)

        return processed_data

    def setup_connections(self):
        """Establish TCP connections to Delsys system"""
        try:
            print("🔌 Establishing connections...")
            # Command connection
            self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.comm_socket.settimeout(10)
            self.comm_socket.connect((self.HOST_IP, 50040))
            print("✅ Command connection established")
            
            # EMG data connection
            self.emg_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.emg_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.emg_socket.settimeout(10)
            self.emg_socket.connect((self.HOST_IP, 50041))
            print("✅ EMG connection established")
            
            # Remove timeouts for data streaming
            self.emg_socket.settimeout(None)
            return True
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.cleanup_connections()
            return False

    def send_command(self, command):
        """Send command to Delsys system"""
        try:
            cmd_bytes = f"{command}\r\n\r\n".encode()
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
            if not self.send_command(f"RATE {int(self.SAMPLING_RATE)}"):
                 return False
                 
            # Query actual rate
            if not self.send_command("RATE?"):
                return False
                
            try:
                response = self.comm_socket.recv(1024).decode().strip()
                print(f"📊 Sampling rate response: {response}")
                
                # Adjust parameters based on response
                if '1925' in response:
                    self.rate_adjusted_bytes = 1664
                    actual_rate = 1925.926
                else:
                    self.rate_adjusted_bytes = 1728
                    actual_rate = 2000.0

                # Update sampling rate and buffers if rate differs
                if actual_rate != self.SAMPLING_RATE:
                    print(f"⚠️  Actual rate {actual_rate}Hz differs from requested {self.SAMPLING_RATE}Hz. Updating...")
                    self.SAMPLING_RATE = actual_rate
                    self._design_filters()

                # Update buffer size based on actual rate
                TARGET_TIME_WINDOW = 1.0
                self.buffer_size = int(self.SAMPLING_RATE * TARGET_TIME_WINDOW)
                self.emg_buffers = [deque(maxlen=self.buffer_size) for _ in range(self.NUM_SENSORS)]
                print(f"✅ Buffer size updated: {self.buffer_size} samples")
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
        self.fig_emg.suptitle('Processed EMG Data (Envelope)', color='white', fontsize=16)
        self.fig_emg.patch.set_facecolor('black')
        self.axes_emg = axes_emg_2d.flatten()
        
        for i in range(self.NUM_SENSORS):
            ax = self.axes_emg[i]
            ax.set_facecolor([0.15, 0.15, 0.15])
            ax.grid(True, color=[0.9725, 0.9725, 0.9725], alpha=0.3)
            ax.tick_params(colors=[0.9725, 0.9725, 0.9725])
            ax.set_ylim([0, 0.002])
            ax.set_xlim([0, self.buffer_size])
            
            # Create empty line
            line, = ax.plot([], [], 'y-', linewidth=1)
            self.lines_emg.append(line)
            
            # Labels
            if i % 4 == 0:
                ax.set_ylabel('Amplitude', color=[0.9725, 0.9725, 0.9725])
            else:
                ax.set_yticklabels([])
            if i >= 12:
                ax.set_xlabel('Samples', color=[0.9725, 0.9725, 0.9725])
            else:
                ax.set_xticklabels([])
            ax.set_title(f'EMG-{i+1} {self.muscle_labels[i]}',
                        color=[0.9725, 0.9725, 0.9725], fontsize=10)
                        
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

    def data_processing_thread(self):
        """Thread to process queued data and update buffers"""
        print("🔄 Data processing thread started")
        while self.streaming:
            try:
                # Process EMG data
                try:
                    emg_data = self.emg_data_queue.get_nowait()
                    # Demultiplex data and accumulate
                    for channel in range(self.NUM_SENSORS):
                        # Get data for this specific channel from the packet
                        channel_data = emg_data[channel::self.NUM_SENSORS]
                        # Add these samples to the processing buffer for this channel
                        self.emg_processing_buffers[channel].extend(channel_data)

                        # Check if we have enough data accumulated to process
                        if len(self.emg_processing_buffers[channel]) >= self.ACCUMULATION_SIZE:
                            # Convert accumulated data to numpy array for processing
                            accumulated_data = np.array(self.emg_processing_buffers[channel])

                            # Apply signal processing to the accumulated chunk
                            processed_channel_data = self.process_emg_channel(accumulated_data)

                            # Extend the main plotting buffer with the processed data
                            self.emg_buffers[channel].extend(processed_channel_data)

                            # Clear the processing buffer for this channel
                            self.emg_processing_buffers[channel].clear()

                except queue.Empty:
                    pass

                # Small sleep to prevent this thread from consuming too much CPU
                time.sleep(0.001)
            except Exception as e:
                if self.streaming:
                    print(f"❌ Processing thread error: {e}")
                    import traceback
                    traceback.print_exc()
                break
        print("🔄 Processing thread stopped")

    def clear_processing_buffers(self):
        """Clear the temporary processing buffers."""
        for buffer in self.emg_processing_buffers:
            buffer.clear()

    def update_plots(self, frame):
        """Animation function to update plots"""
        try:
            # Update EMG plots
            for i in range(self.NUM_SENSORS):
                if len(self.emg_buffers[i]) > 0:
                    y_data = list(self.emg_buffers[i])
                    x_data = list(range(len(y_data)))
                    self.lines_emg[i].set_data(x_data, y_data)
        except Exception as e:
            print(f"❌ Plot update error: {e}")
        return self.lines_emg

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
            threading.Thread(target=self.data_processing_thread, daemon=True)
        ]
        print("🔄 Starting data threads...")
        for thread in self.threads:
            thread.start()
            
        # Start animations
        print("🎬 Starting animations...")
        self.ani_emg = FuncAnimation(self.fig_emg, self.update_plots,
                                    interval=50, blit=False, cache_frame_data=False)
                                    
        # Show plots
        print("📊 Displaying plots...")
        plt.show(block=True)
        return True

    def stop_streaming(self):
        """Stop data acquisition"""
        print("🛑 Stopping streaming...")
        self.clear_processing_buffers()
        self.streaming = False
        # Wait for threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=2.0)
        self.cleanup_connections()

    def cleanup_connections(self):
        """Close all network connections"""
        for sock, name in [(self.comm_socket, "Command"),
                          (self.emg_socket, "EMG")]:
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
    HOST_IP = 'localhost'
    NUM_SENSORS = 16
    SAMPLING_RATE = 2000.0
    
    # Create streamer object
    streamer = DelsysStreamer(host_ip=HOST_IP, num_sensors=NUM_SENSORS, sampling_rate=SAMPLING_RATE)
    print("🔌 Starting Delsys EMG Streamer (Processed)...")
    print("📡 Connecting to system...")
    print("⚠️  Press Ctrl+C to stop")
    
    try:
        if streamer.start_streaming():
            print("✅ Streaming completed")
        else:
            print("❌ Failed to start streaming")
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    try:
        import scipy
    except ImportError:
        print("❌ Error: 'scipy' is required for signal processing. Please install it using 'pip install scipy'")
        sys.exit(1)

    main()