#!/usr/bin/env python3
"""
Thermal-Safe TTS Processing Script
Processes lectures one by one with cooling breaks to prevent overheating
"""

import subprocess
import time
import os
import json
from pathlib import Path

def get_cpu_temperature():
    """Get CPU temperature (requires sudo for powermetrics)"""
    try:
        result = subprocess.run([
            'sudo', 'powermetrics', '--samplers', 'smc', '-n', '1'
        ], capture_output=True, text=True, timeout=10)
        
        for line in result.stdout.split('\n'):
            if 'CPU die temperature' in line:
                # Extract temperature value
                temp_str = line.split(':')[1].strip().replace('°C', '')
                return float(temp_str)
    except:
        pass
    return None

def wait_for_cooling(target_temp=75, max_wait=300):
    """Wait for CPU to cool down to target temperature"""
    print(f"🌡️  Waiting for CPU to cool below {target_temp}°C...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        temp = get_cpu_temperature()
        if temp and temp < target_temp:
            print(f"✅ CPU cooled to {temp:.1f}°C")
            return True
        elif temp:
            print(f"🔥 Current temperature: {temp:.1f}°C (waiting...)")
        
        time.sleep(10)
    
    print(f"⚠️  Timeout waiting for cooling, proceeding anyway")
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

def process_single_lecture(lecture_info):
    """Process a single lecture with thermal monitoring"""
    print(f"\n🎤 Processing: {lecture_info['course']} - {lecture_info['lecture']}")
    
    # Check temperature before starting
    temp = get_cpu_temperature()
    if temp and temp > 80:
        print(f"🔥 Temperature too high ({temp:.1f}°C), cooling first...")
        wait_for_cooling(75)
    
    # Create temporary config for single lecture
    temp_config = {
        "page_07_tts_kokoro": {
            "target_lecture": lecture_info["path"],
            "single_lecture_mode": True
        }
    }
    
    # Run TTS processing
    start_time = time.time()
    try:
        result = subprocess.run([
            'python', 'dreamlet.py', 'run', '07'
        ], capture_output=True, text=True)
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ Completed in {duration:.1f}s")
            return True
        else:
            print(f"❌ Failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main thermal-safe processing function"""
    print("🎬 Thermal-Safe TTS Processing for MacBook Pro M3")
    print("=" * 60)
    
    lectures = get_lectures_to_process()
    if not lectures:
        print("❌ No lectures found for processing")
        return
    
    print(f"📚 Found {len(lectures)} lectures to process")
    
    successful = 0
    failed = 0
    
    for i, lecture in enumerate(lectures, 1):
        print(f"\n📖 [{i}/{len(lectures)}] Processing lecture...")
        
        if process_single_lecture(lecture):
            successful += 1
            
            # Cooling break after each lecture (except last)
            if i < len(lectures):
                print("❄️  Cooling break (30 seconds)...")
                time.sleep(30)
        else:
            failed += 1
            print("⚠️  Continuing to next lecture...")
    
    print(f"\n🎯 Processing Complete!")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {successful/(successful+failed)*100:.1f}%")

if __name__ == "__main__":
    main()