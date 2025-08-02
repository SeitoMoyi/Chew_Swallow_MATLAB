#!/usr/bin/env python3
"""
Real-Time EMG Data Plotter
Consumes processed EMG data from a queue and displays it using Matplotlib.
Designed to be used with data_handler.py.
"""
import threading
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
import queue


class EMGPlotter:
    """
    Handles the visualization of processed EMG data.
    """

    def __init__(self, num_sensors=16, sampling_rate=2000.0, data_queue=None):
        """
        Initialize the EMG plotter.
        Args:
            num_sensors (int): Number of EMG sensors.
            sampling_rate (float): Expected sampling rate (used for buffer sizing).
            data_queue (queue.Queue): Queue from which to receive processed data.
                                      If None, a new queue is created.
        """
        self.NUM_SENSORS = num_sensors
        self.SAMPLING_RATE = sampling_rate
        self.data_queue = data_queue if data_queue is not None else queue.Queue()

        # Circular buffers for processed EMG data (1 second window)
        self.buffer_size = int(self.SAMPLING_RATE * 1.0)
        # Use a dictionary to map channel number to its deque for easier access
        self.emg_buffers = {i: deque(maxlen=self.buffer_size) for i in range(self.NUM_SENSORS)}

        # Plotting objects
        self.fig_emg = None
        self.axes_emg = []
        self.lines_emg = []

        # Muscle labels (should ideally come from the data source)
        self.muscle_labels = [
            'L-TIBI', 'L-GAST', 'L-RECT-DIST', 'L-RECT-PROX', 'L-VAST-LATE',
            'R-TIBI', 'R-GAST', 'R-RECT-DIST', 'R-RECT-PROX', 'R-VAST-LATE',
            'L-SEMI', 'R-SEMI', 'NC', 'NC', 'L-BICEP-FEMO', 'R-BICEP-FEMO'
        ]

        # Threading control for animation
        self.animating = False
        self.ani_emg = None

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

            # Set initial y-limits (might need adjustment based on actual data)
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

    def data_consumer_thread(self):
        """Thread to consume data from the queue and update buffers."""
        print("🔄 Data consumer thread started")
        while self.animating: # Use animating flag for consistency
            try:
                # Get processed data from the queue
                processed_data = self.data_queue.get(timeout=0.1) # Timeout to allow checking flag
                channel = processed_data['channel']
                samples = processed_data['samples']

                # Update the buffer for this channel
                if channel in self.emg_buffers:
                    self.emg_buffers[channel].extend(samples)

            except queue.Empty:
                continue # Check flag again
            except Exception as e:
                 print(f"❌ Data consumer error: {e}")
                 break
        print("🔄 Data consumer thread stopped")

    def update_plots(self, frame):
        """Animation function to update plots"""
        try:
            # Update EMG plots
            for i in range(self.NUM_SENSORS):
                buffer = self.emg_buffers.get(i, deque(maxlen=self.buffer_size))
                if len(buffer) > 0:
                    y_data = list(buffer)
                    x_data = list(range(len(y_data)))
                    self.lines_emg[i].set_data(x_data, y_data)
        except Exception as e:
            print(f"❌ Plot update error: {e}")
        return self.lines_emg

    def start_animation(self):
        """Start the plotting animation."""
        print("🎬 Starting animation...")
        self.setup_plots()
        self.animating = True

        # Start consumer thread
        consumer_thread = threading.Thread(target=self.data_consumer_thread, daemon=True)
        consumer_thread.start()

        # Start animation
        self.ani_emg = FuncAnimation(self.fig_emg, self.update_plots,
                                    interval=50, blit=False, cache_frame_data=False)
        # Show plots
        print("📊 Displaying plots...")
        plt.show(block=True) # This will block until the window is closed
        self.animating = False # Set flag to False when window is closed

    def stop_animation(self):
        """Stop the plotting animation."""
        print("🛑 Stopping animation...")
        self.animating = False
        if self.ani_emg:
            self.ani_emg.event_source.stop() # Stop the animation timer
        plt.close(self.fig_emg) # Close the figure window

# Example usage if run directly (for testing plotter)
if __name__ == "__main__":
    import signal
    import sys
    # Import the data handler to test the integration
    from delsys_handler import DelsysDataHandler

    def signal_handler(sig, frame):
        print("\n🛑 Shutting down plotter...")
        plotter.stop_animation()
        if 'handler' in globals():
             handler.stop_streaming()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Configuration
    HOST_IP = 'localhost' # Replace with actual IP if needed
    NUM_SENSORS = 16
    SAMPLING_RATE = 2000.0

    # Create shared queue
    shared_queue = queue.Queue(maxsize=1000)

    # Create handler object
    handler = DelsysDataHandler(host_ip=HOST_IP, num_sensors=NUM_SENSORS, sampling_rate=SAMPLING_RATE)
    # Override the handler's queue to use the shared one
    handler.output_queue = shared_queue

    # Create plotter object using the shared queue
    plotter = EMGPlotter(num_sensors=NUM_SENSORS, sampling_rate=SAMPLING_RATE, data_queue=shared_queue)

    print("📊 Starting Delsys EMG Plotter...")

    try:
        if handler.start_streaming():
            print("✅ Data streaming started.")
            print("📊 Starting plotter...")
            plotter.start_animation() # This will block
        else:
            print("❌ Failed to start data streaming")
    except KeyboardInterrupt:
        signal_handler(None, None)
    finally:
        handler.stop_streaming()
        plotter.stop_animation()
