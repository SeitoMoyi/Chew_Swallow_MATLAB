#!/usr/bin/env python3
"""
Kivy-based Real-Time EMG and Accelerometer Data Streaming
Modern UI version with better performance and touch support
"""

import socket
import struct
import threading
import time
import numpy as np
from collections import deque
import queue
import signal
import sys

# Kivy imports
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics import Line, Color, Rectangle
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.uix.popup import Popup

class RealTimePlot(Widget):
    """Custom widget for real-time plotting"""
    
    def __init__(self, title="", y_range=(-0.005, 0.005), line_colors=None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.y_min, self.y_max = y_range
        self.line_colors = line_colors or [(1, 1, 0, 1)]  # Default yellow
        self.data_buffers = [deque(maxlen=500) for _ in range(len(self.line_colors))]
        self.lines = []
        
        # Bind size and position changes
        self.bind(size=self._update_graphics, pos=self._update_graphics)
        
        # Initialize graphics
        with self.canvas:
            # Background
            Color(0.15, 0.15, 0.15, 1)  # Dark gray background
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
            # Grid lines (will be updated in _draw_grid)
            Color(0.3, 0.3, 0.3, 0.5)  # Light gray for grid
            
            # Initialize line objects
            for color in self.line_colors:
                Color(*color)
                line = Line(points=[], width=1.5)
                self.lines.append(line)
    
    def _update_graphics(self, *args):
        """Update graphics when widget size/position changes"""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self._draw_grid()
        self._update_plot()
    
    def _draw_grid(self):
        """Draw grid lines"""
        if self.size[0] <= 0 or self.size[1] <= 0:
            return
            
        # Clear existing grid
        with self.canvas:
            Color(0.3, 0.3, 0.3, 0.3)
            
            # Vertical grid lines
            for i in range(0, int(self.size[0]), 50):
                x = self.pos[0] + i
                Line(points=[x, self.pos[1], x, self.pos[1] + self.size[1]], width=0.5)
            
            # Horizontal grid lines
            for i in range(0, int(self.size[1]), 25):
                y = self.pos[1] + i
                Line(points=[self.pos[0], y, self.pos[0] + self.size[0], y], width=0.5)
    
    def add_data(self, buffer_index, data_points):
        """Add new data points to specified buffer"""
        if buffer_index < len(self.data_buffers):
            self.data_buffers[buffer_index].extend(data_points)
    
    def _update_plot(self):
        """Update plot lines with current data"""
        if self.size[0] <= 0 or self.size[1] <= 0:
            return
            
        for i, (buffer, line) in enumerate(zip(self.data_buffers, self.lines)):
            if len(buffer) > 1:
                # Convert data to screen coordinates
                points = []
                x_scale = self.size[0] / max(len(buffer), 1)
                y_scale = self.size[1] / (self.y_max - self.y_min)
                
                for j, value in enumerate(buffer):
                    x = self.pos[0] + j * x_scale
                    y = self.pos[1] + (value - self.y_min) * y_scale
                    # Clamp y to widget bounds
                    y = max(self.pos[1], min(self.pos[1] + self.size[1], y))
                    points.extend([x, y])
                
                # Update line points
                line.points = points
    
    def update_display(self, dt):
        """Called by Kivy Clock to update display"""
        self._update_plot()

class EMGChannelGrid(GridLayout):
    """Grid layout for EMG channel plots"""
    
    def __init__(self, num_sensors=16, muscle_labels=None, **kwargs):
        super().__init__(**kwargs)
        self.cols = 4
        self.rows = 4
        self.spacing = 2
        self.num_sensors = num_sensors
        self.muscle_labels = muscle_labels or [f"CH-{i+1}" for i in range(num_sensors)]
        
        # Create plot widgets for each channel
        self.emg_plots = []
        for i in range(num_sensors):
            # Container for plot and label
            container = BoxLayout(orientation='vertical', spacing=1)
            
            # Title label
            title = Label(
                text=f'EMG-{i+1} {self.muscle_labels[i]}',
                size_hint_y=None,
                height=25,
                color=(0.97, 0.97, 0.97, 1),
                font_size=10
            )
            
            # Plot widget
            plot = RealTimePlot(
                title=f'EMG-{i+1}',
                y_range=(-0.005, 0.005),
                line_colors=[(1, 1, 0, 1)]  # Yellow
            )
            
            container.add_widget(title)
            container.add_widget(plot)
            self.add_widget(container)
            self.emg_plots.append(plot)

class ACCChannelGrid(GridLayout):
    """Grid layout for ACC channel plots"""
    
    def __init__(self, num_sensors=16, **kwargs):
        super().__init__(**kwargs)
        self.cols = 4
        self.rows = 4
        self.spacing = 2
        self.num_sensors = num_sensors
        
        # Create plot widgets for each sensor (3 axes each)
        self.acc_plots = []
        for i in range(num_sensors):
            # Container for plot and label
            container = BoxLayout(orientation='vertical', spacing=1)
            
            # Title label
            title = Label(
                text=f'ACC CH-{i+1}',
                size_hint_y=None,
                height=25,
                color=(0.97, 0.97, 0.97, 1),
                font_size=10
            )
            
            # Plot widget with 3 lines (X=Red, Y=Blue, Z=Green)
            plot = RealTimePlot(
                title=f'ACC-{i+1}',
                y_range=(-8, 8),
                line_colors=[(1, 0, 0, 1), (0, 0, 1, 1), (0, 1, 0, 1)]  # RGB
            )
            
            container.add_widget(title)
            container.add_widget(plot)
            self.add_widget(container)
            self.acc_plots.append(plot)

class ControlPanel(BoxLayout):
    """Control panel with start/stop buttons and status"""
    
    def __init__(self, streamer_app, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = 60
        self.spacing = 10
        self.padding = 10
        
        self.streamer_app = streamer_app
        
        # Start/Stop button
        self.start_btn = Button(
            text='Start Streaming',
            size_hint_x=None,
            width=150,
            background_color=(0, 0.7, 0, 1)
        )
        self.start_btn.bind(on_press=self.toggle_streaming)
        
        # Status label
        self.status_label = Label(
            text='Ready to connect...',
            color=(1, 1, 1, 1)
        )
        
        # Connection info
        self.connection_label = Label(
            text='Host: localhost',
            size_hint_x=None,
            width=200,
            color=(0.8, 0.8, 0.8, 1)
        )
        
        self.add_widget(self.start_btn)
        self.add_widget(self.status_label)
        self.add_widget(self.connection_label)
    
    def toggle_streaming(self, instance):
        """Toggle streaming on/off"""
        if not self.streamer_app.is_streaming:
            self.streamer_app.start_streaming()
        else:
            self.streamer_app.stop_streaming()
    
    def update_status(self, status, color=(1, 1, 1, 1)):
        """Update status label"""
        self.status_label.text = status
        self.status_label.color = color
    
    def update_button(self, is_streaming):
        """Update button state"""
        if is_streaming:
            self.start_btn.text = 'Stop Streaming'
            self.start_btn.background_color = (0.7, 0, 0, 1)
        else:
            self.start_btn.text = 'Start Streaming'
            self.start_btn.background_color = (0, 0.7, 0, 1)

class DelsysStreamerApp(App):
    """Main Kivy application for Delsys streaming"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Configuration
        self.HOST_IP = 'localhost'
        self.NUM_SENSORS = 16
        self.muscle_labels = [
            'L-TIBI', 'L-GAST', 'L-RECT-DIST', 'L-RECT-PROX', 'L-VAST-LATE',
            'R-TIBI', 'R-GAST', 'R-RECT-DIST', 'R-RECT-PROX', 'R-VAST-LATE',
            'L-SEMI', 'R-SEMI', 'NC', 'NC', 'L-BICEP-FEMO', 'R-BICEP-FEMO'
        ]
        
        # Network connections
        self.comm_socket = None
        self.emg_socket = None
        self.acc_socket = None
        
        # Data management
        self.emg_data_queue = queue.Queue(maxsize=1000)
        self.acc_data_queue = queue.Queue(maxsize=1000)
        self.is_streaming = False
        self.threads = []
        
        # Sampling parameters
        self.rate_adjusted_bytes = 1728
        
        # UI components (will be set in build())
        self.emg_grid = None
        self.acc_grid = None
        self.control_panel = None
    
    def build(self):
        """Build the Kivy UI"""
        # Set window properties
        Window.clearcolor = (0.1, 0.1, 0.1, 1)  # Dark background
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical', spacing=5, padding=5)
        
        # Control panel
        self.control_panel = ControlPanel(self)
        main_layout.add_widget(self.control_panel)
        
        # Data display area (split between EMG and ACC)
        data_layout = BoxLayout(orientation='horizontal', spacing=5)
        
        # EMG section
        emg_section = BoxLayout(orientation='vertical', spacing=2)
        emg_title = Label(
            text='EMG Data',
            size_hint_y=None,
            height=30,
            font_size=16,
            color=(1, 1, 1, 1),
            bold=True
        )
        self.emg_grid = EMGChannelGrid(
            num_sensors=self.NUM_SENSORS,
            muscle_labels=self.muscle_labels
        )
        emg_section.add_widget(emg_title)
        emg_section.add_widget(self.emg_grid)
        
        # ACC section
        acc_section = BoxLayout(orientation='vertical', spacing=2)
        acc_title = Label(
            text='Accelerometer Data',
            size_hint_y=None,
            height=30,
            font_size=16,
            color=(1, 1, 1, 1),
            bold=True
        )
        self.acc_grid = ACCChannelGrid(num_sensors=self.NUM_SENSORS)
        acc_section.add_widget(acc_title)
        acc_section.add_widget(self.acc_grid)
        
        # Add sections to data layout
        data_layout.add_widget(emg_section)
        data_layout.add_widget(acc_section)
        
        # Add to main layout
        main_layout.add_widget(data_layout)
        
        # Schedule plot updates
        Clock.schedule_interval(self.update_plots, 1.0/30.0)  # 30 FPS
        Clock.schedule_interval(self.process_data, 1.0/60.0)  # 60 FPS data processing
        
        return main_layout
    
    def setup_connections(self):
        """Establish connections to Delsys system"""
        try:
            self.control_panel.update_status("Connecting...", (1, 1, 0, 1))
            
            # Command connection
            self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.comm_socket.settimeout(5)
            self.comm_socket.connect((self.HOST_IP, 50040))
            
            # EMG connection
            self.emg_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.emg_socket.connect((self.HOST_IP, 50041))
            
            # ACC connection
            self.acc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.acc_socket.connect((self.HOST_IP, 50042))
            
            # Remove timeouts for data sockets
            self.emg_socket.settimeout(None)
            self.acc_socket.settimeout(None)
            
            self.control_panel.update_status("Connected!", (0, 1, 0, 1))
            return True
            
        except Exception as e:
            self.control_panel.update_status(f"Connection failed: {e}", (1, 0, 0, 1))
            return False
    
    def configure_system(self):
        """Configure Delsys system"""
        try:
            # Send commands
            self.comm_socket.send(b"RATE 2000\r\n\r")
            time.sleep(0.1)
            self.comm_socket.send(b"START\r\n\r")
            
            self.control_panel.update_status("System configured", (0, 1, 0, 1))
            return True
            
        except Exception as e:
            self.control_panel.update_status(f"Config failed: {e}", (1, 0, 0, 1))
            return False
    
    def emg_data_thread(self):
        """EMG data acquisition thread"""
        while self.is_streaming:
            try:
                data_bytes = self.emg_socket.recv(self.rate_adjusted_bytes)
                if len(data_bytes) == self.rate_adjusted_bytes:
                    samples = struct.unpack(f'{len(data_bytes)//4}f', data_bytes)
                    samples_array = np.array(samples)
                    
                    try:
                        self.emg_data_queue.put_nowait(samples_array)
                    except queue.Full:
                        try:
                            self.emg_data_queue.get_nowait()
                            self.emg_data_queue.put_nowait(samples_array)
                        except queue.Empty:
                            pass
                            
            except Exception as e:
                if self.is_streaming:
                    print(f"EMG thread error: {e}")
                break
    
    def acc_data_thread(self):
        """ACC data acquisition thread"""
        while self.is_streaming:
            try:
                data_bytes = self.acc_socket.recv(384)
                if len(data_bytes) == 384:
                    samples = struct.unpack(f'{len(data_bytes)//4}f', data_bytes)
                    samples_array = np.array(samples)
                    
                    try:
                        self.acc_data_queue.put_nowait(samples_array)
                    except queue.Full:
                        try:
                            self.acc_data_queue.get_nowait()
                            self.acc_data_queue.put_nowait(samples_array)
                        except queue.Empty:
                            pass
                            
            except Exception as e:
                if self.is_streaming:
                    print(f"ACC thread error: {e}")
                break
    
    def process_data(self, dt):
        """Process incoming data and update plot buffers"""
        if not self.is_streaming:
            return
            
        # Process EMG data
        try:
            while True:
                emg_data = self.emg_data_queue.get_nowait()
                # Demultiplex and add to plot buffers
                for channel in range(self.NUM_SENSORS):
                    channel_data = emg_data[channel::16]
                    self.emg_grid.emg_plots[channel].add_data(0, channel_data)
        except queue.Empty:
            pass
        
        # Process ACC data
        try:
            while True:
                acc_data = self.acc_data_queue.get_nowait()
                # Demultiplex ACC data (48 channels = 16 sensors × 3 axes)
                for sensor in range(self.NUM_SENSORS):
                    for axis in range(3):
                        axis_idx = sensor * 3 + axis
                        if axis_idx < 48:
                            axis_data = acc_data[axis_idx::48]
                            self.acc_grid.acc_plots[sensor].add_data(axis, axis_data)
        except queue.Empty:
            pass
    
    def update_plots(self, dt):
        """Update all plot displays"""
        if not self.is_streaming:
            return
            
        # Update EMG plots
        for plot in self.emg_grid.emg_plots:
            plot.update_display(dt)
        
        # Update ACC plots
        for plot in self.acc_grid.acc_plots:
            plot.update_display(dt)
    
    def start_streaming(self):
        """Start data streaming"""
        if self.is_streaming:
            return
            
        if not self.setup_connections():
            return
            
        if not self.configure_system():
            return
            
        self.is_streaming = True
        self.control_panel.update_button(True)
        self.control_panel.update_status("Streaming...", (0, 1, 0, 1))
        
        # Start data threads
        self.threads = [
            threading.Thread(target=self.emg_data_thread, daemon=True),
            threading.Thread(target=self.acc_data_thread, daemon=True)
        ]
        
        for thread in self.threads:
            thread.start()
    
    def stop_streaming(self):
        """Stop data streaming"""
        if not self.is_streaming:
            return
            
        self.is_streaming = False
        self.control_panel.update_button(False)
        self.control_panel.update_status("Stopped", (1, 1, 0, 1))
        
        # Wait for threads
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1.0)
        
        # Close connections
        for sock in [self.comm_socket, self.emg_socket, self.acc_socket]:
            if sock:
                try:
                    sock.close()
                except:
                    pass
    
    def on_stop(self):
        """Called when app is closing"""
        self.stop_streaming()

def main():
    """Main function"""
    # Create and run the Kivy app
    app = DelsysStreamerApp()
    app.run()

if __name__ == "__main__":
    main()