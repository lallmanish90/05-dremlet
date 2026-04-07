#!/usr/bin/env python3
"""
Thermal-Safe TTS Processing (No Password Required)
Uses CPU monitoring instead of temperature sensors
Includes automatic Kokoro server restart functionality
"""

# KOKORO SERVER CONFIGURATION
# Adjust these settings based on your Kokoro Docker setup
KOKORO_CONFIG = {
    "api_url": "http://localhost:8880/v1",
    "docker_image": "ghcr.io/remsky/kokoro-fastapi-cpu:latest",  # Your actual Kokoro image
    "container_name": "kokoro-tts",
    "port": "8880:8880",
    "use_gpu": False,  # CPU version, no GPU needed
    "startup_timeout": 30  # seconds to wait for server startup
}

import subprocess
import time
import os
import json
import psutil
import requests
from pathlib import Path

def get_system_load():
    """Get system load without sudo"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)  # Faster check
        memory = psutil.virtual_memory()
        
        # Estimate thermal load
        thermal_load = cpu_percent + (memory.percent * 0.3)
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'thermal_load': min(thermal_load, 100)
        }
    except:
        return None

def wait_for_system_cooling(target_load=70, max_wait=120):
    """Wait for system load to decrease"""
    print(f"⏳ Waiting for system load to drop below {target_load}%...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        load_info = get_system_load()
        if load_info and load_info['thermal_load'] < target_load:
            print(f"✅ System load: {load_info['thermal_load']:.1f}% (CPU: {load_info['cpu_percent']:.1f}%)")
            return True
        elif load_info:
            print(f"🔄 Current load: {load_info['thermal_load']:.1f}% (waiting...)")
        
        time.sleep(5)  # Check more frequently
    
    print(f"⚠️  Timeout waiting for cooling, proceeding anyway")
    return False

def check_kokoro_server():
    """Check if Kokoro server is running"""
    try:
        response = requests.get(f"{KOKORO_CONFIG['api_url']}/audio/voices", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_kokoro_server():
    """Start Kokoro server using Docker"""
    print("🚀 Starting Kokoro TTS server...")
    try:
        # Check if Docker is available
        docker_check = subprocess.run(['docker', '--version'], 
                                    capture_output=True, text=True)
        if docker_check.returncode != 0:
            print("❌ Docker not available. Please start Kokoro server manually.")
            return False
        
        # Build Docker command based on configuration
        docker_cmd = [
            'docker', 'run', '-d', '--rm',
            '--name', KOKORO_CONFIG['container_name'],
            '-p', KOKORO_CONFIG['port']
        ]
        
        # Add GPU support if enabled
        if KOKORO_CONFIG['use_gpu']:
            docker_cmd.extend(['--gpus', 'all'])
        
        # Add image name
        docker_cmd.append(KOKORO_CONFIG['docker_image'])
        
        print(f"🐳 Running: {' '.join(docker_cmd)}")
        result = subprocess.run(docker_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Kokoro server starting...")
            # Wait for server to be ready
            for i in range(KOKORO_CONFIG['startup_timeout']):
                time.sleep(1)
                if check_kokoro_server():
                    print("✅ Kokoro server is ready!")
                    return True
                print(f"⏳ Waiting for server... ({i+1}/{KOKORO_CONFIG['startup_timeout']})")
            
            print("⚠️ Server started but not responding. Please check manually.")
            return False
        else:
            print(f"❌ Failed to start server: {result.stderr}")
            # Try alternative command without GPU if GPU command failed
            if KOKORO_CONFIG['use_gpu'] and "could not select device driver" in result.stderr.lower():
                print("🔄 GPU not available, trying without GPU...")
                KOKORO_CONFIG['use_gpu'] = False
                return start_kokoro_server()
            return False
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

def restart_kokoro_server():
    """Restart Kokoro server"""
    print("🔄 Restarting Kokoro TTS server...")
    try:
        # Stop existing container
        subprocess.run(['docker', 'stop', KOKORO_CONFIG['container_name']], 
                      capture_output=True, text=True)
        time.sleep(2)
        
        # Start new container
        return start_kokoro_server()
    except Exception as e:
        print(f"❌ Error restarting server: {e}")
        return False

def get_lectures_to_process():
    """Get list of lectures that need TTS processing"""
    lectures = []
    input_dir = Path("input")
    
    for course_dir in input_dir.iterdir():
        if course_dir.is_dir():
            for lecture_dir in course_dir.iterdir():
                if lecture_dir.is_dir() and "lecture" in lecture_dir.name.lower():
                    english_text = lecture_dir / "English text"
                    if english_text.exists():
                        lectures.append({
                            "course": course_dir.name,
                            "lecture": lecture_dir.name,
                            "path": str(lecture_dir)
                        })
    
    return sorted(lectures, key=lambda x: (x["course"], x["lecture"]))



def main():
    """Main thermal-safe processing function (no password required)"""
    print("🎬 Thermal-Safe TTS Processing (No Password Required)")
    print("=" * 60)
    print("💡 Using CPU load monitoring instead of temperature sensors")
    
    # Check if psutil is available
    try:
        import psutil
        print(f"✅ System monitoring available (psutil version: {psutil.__version__})")
    except ImportError:
        print("❌ psutil not installed. Install with: pip install psutil")
        return
    
    lectures = get_lectures_to_process()
    if not lectures:
        print("❌ No lectures found for processing")
        return
    
    print(f"📚 Found {len(lectures)} lectures to process")
    
    # Check and start Kokoro server if needed
    if not check_kokoro_server():
        print("⚠️ Kokoro server not running, attempting to start...")
        if not start_kokoro_server():
            print("❌ Could not start Kokoro server. Please start it manually.")
            return
    else:
        print("✅ Kokoro server is running")
    
    # Check system load before starting
    load_info = get_system_load()
    if load_info:
        print(f"📊 Current system load: {load_info['thermal_load']:.1f}% (CPU: {load_info['cpu_percent']:.1f}%)")
        if load_info['thermal_load'] > 85:
            print(f"🔥 System load too high, cooling first...")
            wait_for_system_cooling(75)
        else:
            print(f"✅ System load acceptable, proceeding...")
    else:
        print("⚠️  Cannot monitor system load, proceeding with caution...")
    
    # Run TTS processing with retry logic
    max_retries = 3
    successful = 0
    failed = 0
    
    for attempt in range(max_retries):
        print(f"\n🎤 Processing attempt {attempt + 1}/{max_retries}...")
        
        start_time = time.time()
        try:
            result = subprocess.run([
                'python3', 'dreamlet.py', 'run', '07'
            ], capture_output=True, text=True)
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ All lectures completed in {duration:.1f}s")
                successful = len(lectures)
                failed = 0
                break
            elif result.returncode == 2:
                # Partial success (some errors but processing continued)
                print(f"⚠️ Completed with some errors in {duration:.1f}s")
                print("🔄 Checking if server restart is needed...")
                
                if not check_kokoro_server():
                    print("🔄 Server appears down, restarting...")
                    if restart_kokoro_server():
                        print("✅ Server restarted, retrying...")
                        continue
                    else:
                        print("❌ Could not restart server")
                        break
                else:
                    print("✅ Server still running, processing completed with partial success")
                    successful = len(lectures)
                    failed = 0
                    break
            else:
                print(f"❌ Processing failed: {result.stderr}")
                
                # Check if it's a server connection issue
                if "Cannot connect to Kokoro API" in result.stderr:
                    print("🔄 Server connection issue, attempting restart...")
                    if restart_kokoro_server():
                        print("✅ Server restarted, retrying...")
                        continue
                    else:
                        print("❌ Could not restart server")
                        break
                else:
                    # Other error, don't retry
                    break
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            
        # If we get here, there was an error. Wait before retry.
        if attempt < max_retries - 1:
            print("⏳ Waiting 10 seconds before retry...")
            time.sleep(10)
    
    # Final status
    if successful == 0:
        failed = len(lectures)
    
    print(f"\n🎯 Processing Complete!")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {successful/(successful+failed)*100:.1f}%")

def configure_kokoro():
    """Interactive configuration for Kokoro Docker settings"""
    print("🔧 Kokoro Server Configuration")
    print("=" * 40)
    
    print(f"Current Docker image: {KOKORO_CONFIG['docker_image']}")
    new_image = input("Enter Docker image name (press Enter to keep current): ").strip()
    if new_image:
        KOKORO_CONFIG['docker_image'] = new_image
    
    print(f"Current GPU usage: {KOKORO_CONFIG['use_gpu']}")
    gpu_choice = input("Use GPU? (y/n, press Enter to keep current): ").strip().lower()
    if gpu_choice in ['y', 'yes']:
        KOKORO_CONFIG['use_gpu'] = True
    elif gpu_choice in ['n', 'no']:
        KOKORO_CONFIG['use_gpu'] = False
    
    print(f"Current port: {KOKORO_CONFIG['port']}")
    new_port = input("Enter port mapping (press Enter to keep current): ").strip()
    if new_port:
        KOKORO_CONFIG['port'] = new_port
    
    print("\n✅ Configuration updated!")
    print("You can modify the KOKORO_CONFIG section at the top of this file for permanent changes.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "configure":
        configure_kokoro()
    else:
        main()