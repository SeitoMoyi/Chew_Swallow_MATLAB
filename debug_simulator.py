#!/usr/bin/env python3
"""
Debug version of Delsys Simulator with detailed logging
"""

import socket
import struct
import time
import threading
import math
import random

class DelsysSimulatorDebug:
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
        self.sampling_rate = 2000
        self.num_sensors = 16
        self.packet_size_emg = 1728
        self.packet_size_acc = 384
        
        # Signal generation parameters
        self.time_counter = 0
        self.base_frequency = 10
        
    def start_server(self):
        """Start the simulation server with detailed logging"""
        try:
            print("🔧 Setting up sockets...")
            
            # Create and configure EMG socket
            print("📡 Creating EMG socket...")
            self.emg_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.emg_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print(f"📡 Binding EMG socket to {self.host}:{self.emg_port}")
            self.emg_socket.bind((self.host, self.emg_port))
            self.emg_socket.listen(1)
            print("✅ EMG socket ready")
            
            # Create and configure ACC socket
            print("📡 Creating ACC socket...")
            self.acc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.acc_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print(f"📡 Binding ACC socket to {self.host}:{self.acc_port}")
            self.acc_socket.bind((self.host, self.acc_port))
            self.acc_socket.listen(1)
            print("✅ ACC socket ready")
            
            # Create and configure Command socket
            print("📡 Creating Command socket...")
            self.comm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.comm_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print(f"📡 Binding Command socket to {self.host}:{self.comm_port}")
            self.comm_socket.bind((self.host, self.comm_port))
            self.comm_socket.listen(1)
            print("✅ Command socket ready")
            
            print(f"\n🚀 Delsys Simulator started on {self.host}")
            print(f"   EMG Port: {self.emg_port}")
            print(f"   ACC Port: {self.acc_port}")
            print(f"   Command Port: {self.comm_port}")
            print("🔄 Starting connection handler threads...")
            
            # Set running flag BEFORE starting threads
            self.running = True
            
            # Start server threads
            emg_thread = threading.Thread(target=self._handle_emg_connections, daemon=True)
            acc_thread = threading.Thread(target=self._handle_acc_connections, daemon=True)
            comm_thread = threading.Thread(target=self._handle_comm_connections, daemon=True)
            
            print("🔄 Starting EMG thread...")
            emg_thread.start()
            print("🔄 Starting ACC thread...")
            acc_thread.start()
            print("🔄 Starting Command thread...")
            comm_thread.start()
            
            print("✅ All threads started, waiting for connections...")
            print("💡 Try connecting now!")
            
            # Keep server running
            try:
                while self.running:
                    time.sleep(1)
                    # Print status every 10 seconds
                    if int(time.time()) % 10 == 0:
                        print(f"📊 Server running... Connected clients: {list(self.clients.keys())}")
            except KeyboardInterrupt:
                print("\n🛑 Shutting down simulator...")
                self.stop_server()
                
        except Exception as e:
            print(f"❌ Server error: {e}")
            import traceback
            traceback.print_exc()
            
    def _handle_emg_connections(self):
        """Handle EMG data client connections with logging"""
        print("🔄 EMG connection handler started")
        while self.running:
            try:
                print("📡 EMG handler waiting for connection...")
                client_socket, addr = self.emg_socket.accept()
                print(f"✅ EMG client connected from {addr}")
                self.clients['emg'] = client_socket
                
                # Start data sending thread
                data_thread = threading.Thread(target=self._send_emg_data, args=(client_socket,), daemon=True)
                data_thread.start()
                print("🔄 EMG data thread started")
                
            except Exception as e:
                if self.running:
                    print(f"❌ EMG socket error: {e}")
                break
                
    def _handle_acc_connections(self):
        """Handle ACC data client connections with logging"""
        print("🔄 ACC connection handler started")
        while self.running:
            try:
                print("📡 ACC handler waiting for connection...")
                client_socket, addr = self.acc_socket.accept()
                print(f"✅ ACC client connected from {addr}")
                self.clients['acc'] = client_socket
                
                # Start data sending thread
                data_thread = threading.Thread(target=self._send_acc_data, args=(client_socket,), daemon=True)
                data_thread.start()
                print("🔄 ACC data thread started")
                
            except Exception as e:
                if self.running:
                    print(f"❌ ACC socket error: {e}")
                break
                
    def _handle_comm_connections(self):
        """Handle command client connections with logging"""
        print("🔄 Command connection handler started")
        while self.running:
            try:
                print("📡 Command handler waiting for connection...")
                client_socket, addr = self.comm_socket.accept()
                print(f"✅ Command client connected from {addr}")
                self.clients['comm'] = client_socket
                
                # Start command handling thread
                cmd_thread = threading.Thread(target=self._handle_commands, args=(client_socket,), daemon=True)
                cmd_thread.start()
                print("🔄 Command handling thread started")
                
            except Exception as e:
                if self.running:
                    print(f"❌ Command socket error: {e}")
                break
                
    def _handle_commands(self, client_socket):
        """Handle incoming commands with logging"""
        print("🔄 Command handler ready for commands")
        try:
            while self.running:
                print("👂 Waiting for command...")
                data = client_socket.recv(1024)
                if not data:
                    print("❌ No data received, client disconnected")
                    break
                    
                command = data.decode().strip()
                print(f"📨 Received command: '{command}'")
                
                if "RATE?" in command:
                    response = "2000\r\n"
                    client_socket.send(response.encode())
                    print(f"📤 Sent response: '{response.strip()}'")
                elif "RATE" in command and "?" not in command:
                    try:
                        rate_value = command.split()[1]
                        self.sampling_rate = float(rate_value)
                        print(f"⚙️ Set sampling rate to: {self.sampling_rate}")
                    except:
                        print("❌ Invalid rate command format")
                elif "START" in command:
                    print("▶️ Start command received - streaming enabled")
                elif "STOP" in command:
                    print("⏹️ Stop command received")
                    
        except Exception as e:
            print(f"❌ Command handling error: {e}")
            import traceback
            traceback.print_exc()
            
    def _send_emg_data(self, client_socket):
        """Generate and send EMG data packets with logging"""
        samples_per_packet = 27
        packet_rate = self.sampling_rate / samples_per_packet
        packet_interval = 1.0 / packet_rate
        
        print(f"📊 EMG packet rate: {packet_rate:.1f} packets/sec")
        packet_count = 0
        
        try:
            while self.running:
                # Generate synthetic EMG data
                emg_data = self._generate_emg_packet()
                
                # Send data
                try:
                    client_socket.send(emg_data)
                    packet_count += 1
                    if packet_count % 100 == 0:  # Log every 100 packets
                        print(f"📤 Sent {packet_count} EMG packets")
                except:
                    print("❌ EMG client disconnected")
                    break
                    
                time.sleep(packet_interval)
                
        except Exception as e:
            print(f"❌ EMG data sending error: {e}")
            
    def _send_acc_data(self, client_socket):
        """Generate and send ACC data packets with logging"""
        acc_packet_rate = 74
        packet_interval = 1.0 / acc_packet_rate
        
        print(f"📊 ACC packet rate: {acc_packet_rate} packets/sec")
        packet_count = 0
        
        try:
            while self.running:
                # Generate synthetic ACC data
                acc_data = self._generate_acc_packet()
                
                # Send data
                try:
                    client_socket.send(acc_data)
                    packet_count += 1
                    if packet_count % 100 == 0:  # Log every 100 packets
                        print(f"📤 Sent {packet_count} ACC packets")
                except:
                    print("❌ ACC client disconnected")
                    break
                    
                time.sleep(packet_interval)
                
        except Exception as e:
            print(f"❌ ACC data sending error: {e}")
            
    def _generate_emg_packet(self):
        """Generate a packet of synthetic EMG data"""
        samples_per_packet = self.packet_size_emg // 4
        samples_per_channel = samples_per_packet // self.num_sensors
        
        emg_values = []
        
        for i in range(samples_per_channel):
            for channel in range(self.num_sensors):
                time_point = self.time_counter + i / self.sampling_rate
                base_signal = math.sin(2 * math.pi * (self.base_frequency + channel) * time_point)
                noise = random.gauss(0, 0.1)
                activation = 0.5 * math.sin(2 * math.pi * 0.5 * time_point) + 0.5
                muscle_signal = activation * base_signal
                final_value = (muscle_signal + noise) * 0.002
                emg_values.append(final_value)
                
        self.time_counter += samples_per_channel / self.sampling_rate
        packed_data = struct.pack(f'{len(emg_values)}f', *emg_values)
        return packed_data
        
    def _generate_acc_packet(self):
        """Generate a packet of synthetic ACC data"""
        samples_per_packet = 96 // 48
        acc_values = []
        
        for i in range(samples_per_packet):
            for sensor in range(self.num_sensors):
                for axis in range(3):
                    time_point = self.time_counter + i / 100.0
                    
                    if axis == 0:
                        value = math.sin(2 * math.pi * 1 * time_point + sensor * 0.1)
                    elif axis == 1:
                        value = math.cos(2 * math.pi * 1.5 * time_point + sensor * 0.1)
                    else:
                        value = math.sin(2 * math.pi * 0.7 * time_point + sensor * 0.1)
                        
                    if axis == 2:
                        value += 1.0
                        
                    value += random.gauss(0, 0.05)
                    acc_values.append(value)
                    
        packed_data = struct.pack(f'{len(acc_values)}f', *acc_values)
        return packed_data
        
    def stop_server(self):
        """Stop the simulation server"""
        print("🛑 Stopping server...")
        self.running = False
        
        # Close client connections
        for client_type, client_socket in self.clients.items():
            try:
                client_socket.close()
                print(f"✅ Closed {client_type} connection")
            except:
                pass
                
        # Close server sockets
        for sock in [self.emg_socket, self.acc_socket, self.comm_socket]:
            if sock:
                try:
                    sock.close()
                except:
                    pass
                    
        print("✅ Delsys Simulator stopped")

def main():
    """Main function to run the debug simulator"""
    import sys
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = 'localhost'
        
    simulator = DelsysSimulatorDebug(host=host)
    
    print("🔧 Starting Debug Delsys Signal Simulator...")
    print("Press Ctrl+C to stop")
    
    try:
        simulator.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Stopping simulator...")
        simulator.stop_server()

if __name__ == "__main__":
    main()