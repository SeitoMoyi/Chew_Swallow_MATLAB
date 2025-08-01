#!/usr/bin/env python3
"""
Test script to verify simulator and client work together
"""
import subprocess
import time
import sys
import os

def test_connection():
    """Test if simulator is responding"""
    import socket
    
    try:
        # Test command connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('localhost', 50040))
        
        # Send rate query
        sock.send(b"RATE?\r\n\r")
        response = sock.recv(1024)
        print(f"✅ Simulator response: {response.decode().strip()}")
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def run_test_sequence():
    """Run complete test sequence"""
    print("🧪 Testing Delsys Simulator Setup")
    print("=" * 40)
    
    # Check if simulator is running
    if not test_connection():
        print("\n📋 To run the test:")
        print("1. Terminal 1: python delsys_simulator.py")
        print("2. Terminal 2: python test_setup.py")
        return
    
    print("✅ Simulator is running and responding")
    
    # Test data connections
    import socket
    
    try:
        # Test EMG connection
        emg_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        emg_sock.connect(('localhost', 50041))
        print("✅ EMG port connection successful")
        
        # Test ACC connection  
        acc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        acc_sock.connect(('localhost', 50042))
        print("✅ ACC port connection successful")
        
        # Test data reception
        emg_sock.settimeout(2)
        acc_sock.settimeout(2)
        
        emg_data = emg_sock.recv(1728)
        acc_data = acc_sock.recv(384)
        
        print(f"✅ Received EMG data: {len(emg_data)} bytes")
        print(f"✅ Received ACC data: {len(acc_data)} bytes")
        
        emg_sock.close()
        acc_sock.close()
        
        print("\n🎉 All tests passed! Ready to run your EMG client.")
        
    except Exception as e:
        print(f"❌ Data connection test failed: {e}")

if __name__ == "__main__":
    run_test_sequence()