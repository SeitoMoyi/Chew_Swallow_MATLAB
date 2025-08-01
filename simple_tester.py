#!/usr/bin/env python3
"""
Simple connection tester for debugging
"""
import socket
import time

def test_single_connection(host='localhost', port=50040):
    """Test a single connection"""
    print(f"🔌 Testing connection to {host}:{port}")
    
    try:
        # Create socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5 second timeout
        
        print(f"📡 Connecting to {host}:{port}...")
        sock.connect((host, port))
        print("✅ Connection successful!")
        
        if port == 50040:  # Command port
            print("📨 Sending RATE? command...")
            sock.send(b"RATE?\r\n\r")
            
            print("👂 Waiting for response...")
            response = sock.recv(1024)
            print(f"📤 Received: {response}")
            
        sock.close()
        print("✅ Connection closed cleanly")
        return True
        
    except socket.timeout:
        print("❌ Connection timed out")
        return False
    except ConnectionRefusedError:
        print("❌ Connection refused - is the server running?")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def test_all_ports():
    """Test all three ports"""
    print("🧪 Testing all Delsys simulator ports")
    print("=" * 50)
    
    ports = [
        (50040, "Command"),
        (50041, "EMG Data"),
        (50042, "ACC Data")
    ]
    
    results = {}
    
    for port, name in ports:
        print(f"\n🔍 Testing {name} port ({port}):")
        results[port] = test_single_connection(port=port)
        time.sleep(1)  # Brief pause between tests
    
    print("\n📊 Summary:")
    print("=" * 30)
    for port, name in ports:
        status = "✅ PASS" if results[port] else "❌ FAIL"
        print(f"{name:12} ({port}): {status}")
    
    if all(results.values()):
        print("\n🎉 All tests passed! Simulator is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check simulator setup.")

if __name__ == "__main__":
    test_all_ports()