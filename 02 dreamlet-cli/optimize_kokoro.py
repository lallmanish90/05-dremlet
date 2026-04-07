#!/usr/bin/env python3
"""
Kokoro Server Optimization Script
Configures Kokoro for thermal-efficient processing
"""

import requests
import json

def optimize_kokoro_server():
    """Configure Kokoro server for thermal efficiency"""
    
    api_url = "http://localhost:8880/v1"
    
    # Thermal-optimized settings
    optimization_config = {
        "model_settings": {
            "batch_size": 1,           # Process one at a time
            "max_length": 1000,        # Shorter segments
            "temperature": 0.7,        # Slightly lower for efficiency
            "use_gpu": True,           # Use GPU efficiently
            "precision": "fp16"        # Half precision for less heat
        },
        "server_settings": {
            "max_concurrent": 1,       # One request at a time
            "queue_size": 3,           # Small queue
            "timeout": 30,             # Reasonable timeout
            "enable_caching": True     # Cache for repeated text
        }
    }
    
    try:
        # Check if server is running
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Kokoro server is running")
            
            # Apply optimizations (if API supports it)
            try:
                config_response = requests.post(
                    f"{api_url}/config", 
                    json=optimization_config,
                    timeout=10
                )
                if config_response.status_code == 200:
                    print("✅ Applied thermal optimizations to Kokoro server")
                else:
                    print("⚠️  Server doesn't support configuration API")
            except:
                print("ℹ️  Using default server settings")
            
            return True
        else:
            print("❌ Kokoro server not responding properly")
            return False
            
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to Kokoro server")
        return False

def get_server_status():
    """Get current server status and recommendations"""
    api_url = "http://localhost:8880/v1"
    
    try:
        # Get available voices (this tells us server capability)
        voices_response = requests.get(f"{api_url}/audio/voices", timeout=5)
        if voices_response.status_code == 200:
            voices = voices_response.json()
            voice_count = len(voices.get("voices", []))
            
            print(f"🎤 Server has {voice_count} voices available")
            print(f"🔧 Recommended settings for M3 Pro:")
            print(f"   - Use single requests (no batching)")
            print(f"   - 2-3 second delays between requests")
            print(f"   - Process 3-5 files then pause")
            print(f"   - Monitor temperature every 10 files")
            
            return True
    except:
        pass
    
    return False

if __name__ == "__main__":
    print("🔧 Kokoro Server Optimization for MacBook Pro M3")
    print("=" * 50)
    
    if optimize_kokoro_server():
        get_server_status()
    else:
        print("❌ Could not optimize server - check if Kokoro is running")