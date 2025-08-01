#!/usr/bin/env python3
"""
Delsys Signal Simulator
Simulates data streaming from Delsys sensors for testing purposes
"""

import socket
import struct
import time
import threading
import math
import random

class DelsysSimulator:
    def __init__(self, host='localhost', emg_port=50041, acc_port=50042, comm_port=50040):
        self.host = host
        self.emg_port = emg_port
        self.acc_port = acc_port
        self.comm_port = comm_port
        
        self.emg_socket = None
        self.acc_socket = None
        self.comm_socket = None
        
        self.running = False
        self.clients = {}
        
        # Simulation parameters
        self.sampling_rate = 2000  # Hz
        self.num_sensors = 16
        self.packet_size_emg = 1728  # bytes (432 floats * 4 bytes)
        self.packet_size_acc = 384   # bytes (96 floats * 4 bytes)
        
        # Signal generation parameters
        self.time_counter = 0
        self.base_frequency = 10  # Hz
        
    def start_server(self):
        """Start the simulation server"""
        try:
            # Create sockets for each data stream
            self.emg_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.emg_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.emg_socket.bind((self.host, self.emg_port))
            self.emg_socket.listen(1)
            
            self.acc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.acc_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.acc_socket.bind((self.host, self.acc_port))
            self.acc_socket.listen(1)
            
            self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.comm_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.comm_socket.bind((self.host, self.comm_port))
            self.comm_socket.listen(1)
            
            print(f"Delsys Simulator started on {self.host}")
            print(f"EMG Port: {self.emg_port}")
            print(f"ACC Port: {self.acc_port}")
            print(f"Command Port: {self.comm_port}")
            
            # Start server threads
            threading.Thread(target=self._handle_emg_connections, daemon=True).start()
            threading.Thread(target=self._handle_acc_connections, daemon=True).start()
            threading.Thread(target=self._handle_comm_connections, daemon=True).start()
            
            self.running = True
            
            # Keep server running
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down simulator...")
                self.stop_server()
                
        except Exception as e:
            print(f"Server error: {e}")
            
    def _handle_emg_connections(self):
        """Handle EMG data client connections"""
        while self.running:
            try:
                client_socket, addr = self.emg_socket.accept()
                print(f"EMG client connected from {addr}")
                self.clients['emg'] = client_socket
                threading.Thread(target=self._send_emg_data, args=(client_socket,), daemon=True).start()
            except:
                if self.running:
                    print("EMG socket error")
                break
                
    def _handle_acc_connections(self):
        """Handle ACC data client connections"""
        while self.running:
            try:
                client_socket, addr = self.acc_socket.accept()
                print(f"ACC client connected from {addr}")
                self.clients['acc'] = client_socket
                threading.Thread(target=self._send_acc_data, args=(client_socket,), daemon=True).start()
            except:
                if self.running:
                    print("ACC socket error")
                break
                
    def _handle_comm_connections(self):
        """Handle command client connections"""
        while self.running:
            try:
                client_socket, addr = self.comm_socket.accept()
                print(f"Command client connected from {addr}")
                self.clients['comm'] = client_socket
                threading.Thread(target=self._handle_commands, args=(client_socket,), daemon=True).start()
            except:
                if self.running:
                    print("Command socket error")
                break
                
    # Fix for _handle_commands method
    def _handle_commands(self, client_socket):
        """Handle incoming commands"""
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                    
                command = data.decode().strip()
                print(f"Received command: {command}")
                
                if "RATE?" in command:
                    # Respond with exact format expected by client
                    response = "2000\r\n"  # or "1925.926\r\n" to test the other branch
                    client_socket.send(response.encode())
                    print(f"Sent rate response: {response.strip()}")
                elif "RATE" in command and "?" not in command:
                    # Set rate command - extract the rate value
                    try:
                        rate_value = command.split()[1]
                        self.sampling_rate = float(rate_value)
                        print(f"Set sampling rate to: {self.sampling_rate}")
                    except:
                        print("Invalid rate command format")
                elif "START" in command:
                    print("✅ Start command received - streaming enabled")
                elif "STOP" in command:
                    print("⏹️ Stop command received - streaming disabled")
                        
        except Exception as e:
            print(f"Command handling error: {e}")

    # Fix for EMG packet timing
    def _send_emg_data(self, client_socket):
        """Generate and send EMG data packets"""
        # Calculate proper timing based on actual protocol
        samples_per_packet = 27  # 27 samples per channel
        packet_rate = self.sampling_rate / samples_per_packet  # ~74 packets/second
        packet_interval = 1.0 / packet_rate
        
        print(f"EMG packet rate: {packet_rate:.1f} packets/sec")
        
        try:
            while self.running:
                # Generate synthetic EMG data
                emg_data = self._generate_emg_packet()
                
                # Send data
                try:
                    client_socket.send(emg_data)
                except:
                    print("EMG client disconnected")
                    break
                    
                # Wait for next packet
                time.sleep(packet_interval)
                
        except Exception as e:
            print(f"EMG data sending error: {e}")

    # Fix for ACC packet timing
    def _send_acc_data(self, client_socket):
        """Generate and send ACC data packets"""
        # ACC rate is ~148Hz (2000/13.5), packets contain 2 samples
        # So packet rate should be ~74 packets/second (same as EMG to maintain ratio)
        acc_packet_rate = 74  # packets/second
        packet_interval = 1.0 / acc_packet_rate
        
        print(f"ACC packet rate: {acc_packet_rate} packets/sec")
        
        try:
            while self.running:
                # Generate synthetic ACC data
                acc_data = self._generate_acc_packet()
                
                # Send data
                try:
                    client_socket.send(acc_data)
                except:
                    print("ACC client disconnected")
                    break
                    
                time.sleep(packet_interval)
                
        except Exception as e:
            print(f"ACC data sending error: {e}")
            
    def _generate_emg_packet(self):
        """Generate a packet of synthetic EMG data"""
        # Calculate number of samples per packet
        samples_per_packet = self.packet_size_emg // 4  # 432 samples
        samples_per_channel = samples_per_packet // self.num_sensors  # 27 samples per channel
        
        # Generate interleaved EMG data
        emg_values = []
        
        for i in range(samples_per_channel):
            for channel in range(self.num_sensors):
                # Create synthetic EMG signal - combination of sine wave and noise
                time_point = self.time_counter + i / self.sampling_rate
                
                # Base signal with different frequencies for different channels
                base_signal = math.sin(2 * math.pi * (self.base_frequency + channel) * time_point)
                
                # Add some noise
                noise = random.gauss(0, 0.1)
                
                # Add muscle activation pattern (bursts)
                activation = 0.5 * math.sin(2 * math.pi * 0.5 * time_point) + 0.5  # 0.5-1.0 range
                muscle_signal = activation * base_signal
                
                # Scale to typical EMG range
                final_value = (muscle_signal + noise) * 0.002  # Scale to millivolt range
                
                emg_values.append(final_value)
                
        self.time_counter += samples_per_channel / self.sampling_rate
        
        # Pack as bytes (float32)
        packed_data = struct.pack(f'{len(emg_values)}f', *emg_values)
        return packed_data
        
    def _generate_acc_packet(self):
        """Generate a packet of synthetic ACC data"""
        # ACC packet: 384 bytes = 96 float values
        # 16 sensors * 3 axes = 48 axes
        # Multiple samples per packet
        samples_per_packet = 96 // 48  # 2 samples per axis
        
        acc_values = []
        
        for i in range(samples_per_packet):
            for sensor in range(self.num_sensors):
                for axis in range(3):  # X, Y, Z
                    time_point = self.time_counter + i / 100.0  # ACC at ~100Hz
                    
                    # Different motion patterns for different axes
                    if axis == 0:  # X-axis - lateral movement
                        value = math.sin(2 * math.pi * 1 * time_point + sensor * 0.1)
                    elif axis == 1:  # Y-axis - vertical movement
                        value = math.cos(2 * math.pi * 1.5 * time_point + sensor * 0.1)
                    else:  # Z-axis - forward/backward
                        value = math.sin(2 * math.pi * 0.7 * time_point + sensor * 0.1)
                        
                    # Add gravity component to Z-axis
                    if axis == 2:
                        value += 1.0  # Gravity
                        
                    # Add noise
                    value += random.gauss(0, 0.05)
                    
                    acc_values.append(value)
                    
        # Pack as bytes (float32)
        packed_data = struct.pack(f'{len(acc_values)}f', *acc_values)
        return packed_data
        
    def stop_server(self):
        """Stop the simulation server"""
        self.running = False
        
        # Close client connections
        for client_type, client_socket in self.clients.items():
            try:
                client_socket.close()
                print(f"Closed {client_type} connection")
            except:
                pass
                
        # Close server sockets
        for sock in [self.emg_socket, self.acc_socket, self.comm_socket]:
            if sock:
                try:
                    sock.close()
                except:
                    pass
                    
        print("Delsys Simulator stopped")

def main():
    """Main function to run the simulator"""
    import sys
    
    # Get port from command line arguments or use defaults
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = 'localhost'
        
    simulator = DelsysSimulator(host=host)
    
    print("Starting Delsys Signal Simulator...")
    print("Press Ctrl+C to stop")
    
    try:
        simulator.start_server()
    except KeyboardInterrupt:
        print("\nStopping simulator...")
        simulator.stop_server()

if __name__ == "__main__":
    main()