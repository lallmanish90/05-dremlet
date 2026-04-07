#!/usr/bin/env python3
"""
Real-Time Thermal Monitor for TTS Processing
Monitors temperature and automatically pauses processing when too hot
"""

import subprocess
import time
import threading
import signal
import sys
from datetime import datetime

class ThermalMonitor:
    def __init__(self, max_temp=85, warning_temp=80):
        self.max_temp = max_temp
        self.warning_temp = warning_temp
        self.monitoring = False
        self.current_temp = None
        self.temp_history = []
        
    def get_cpu_temperature(self):
        """Get current CPU temperature"""
        try:
            result = subprocess.run([
                'sudo', 'powermetrics', '--samplers', 'smc', '-n', '1'
            ], capture_output=True, text=True, timeout=10)
            
            for line in result.stdout.split('\n'):
                if 'CPU die temperature' in line:
                    temp_str = line.split(':')[1].strip().replace('°C', '')
                    return float(temp_str)
        except:
            pass
        return None
    
    def monitor_loop(self):
        """Continuous temperature monitoring"""
        while self.monitoring:
            temp = self.get_cpu_temperature()
            if temp:
                self.current_temp = temp
                self.temp_history.append({
                    'time': datetime.now(),
                    'temp': temp
                })
                
                # Keep only last 60 readings (10 minutes at 10s intervals)
                if len(self.temp_history) > 60:
                    self.temp_history.pop(0)
                
                # Temperature warnings
                if temp >= self.max_temp:
                    print(f"\n🚨 CRITICAL: CPU at {temp:.1f}°C - PAUSING PROCESSING!")
                    self.pause_processing()
                elif temp >= self.warning_temp:
                    print(f"\n⚠️  WARNING: CPU at {temp:.1f}°C - Consider pausing")
                
            time.sleep(10)  # Check every 10 seconds
    
    def pause_processing(self):
        """Pause processing until temperature drops"""
        print("❄️  Waiting for CPU to cool down...")
        
        while self.current_temp and self.current_temp >= self.warning_temp:
            time.sleep(15)
            temp = self.get_cpu_temperature()
            if temp:
                self.current_temp = temp
                print(f"🌡️  Current: {temp:.1f}°C (target: <{self.warning_temp}°C)")
        
        print(f"✅ CPU cooled to {self.current_temp:.1f}°C - Resuming processing")
    
    def start_monitoring(self):
        """Start temperature monitoring in background"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print(f"🌡️  Thermal monitoring started (max: {self.max_temp}°C)")
    
    def stop_monitoring(self):
        """Stop temperature monitoring"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1)
        print("🛑 Thermal monitoring stopped")
    
    def get_thermal_report(self):
        """Generate thermal performance report"""
        if not self.temp_history:
            return "No temperature data collected"
        
        temps = [reading['temp'] for reading in self.temp_history]
        avg_temp = sum(temps) / len(temps)
        max_temp = max(temps)
        min_temp = min(temps)
        
        report = f"""
🌡️  Thermal Performance Report:
   Average Temperature: {avg_temp:.1f}°C
   Maximum Temperature: {max_temp:.1f}°C
   Minimum Temperature: {min_temp:.1f}°C
   Readings Collected: {len(temps)}
   Time Monitored: {len(temps) * 10 / 60:.1f} minutes
        """
        
        if max_temp >= self.max_temp:
            report += f"\n🚨 CRITICAL temperatures reached!"
        elif max_temp >= self.warning_temp:
            report += f"\n⚠️  High temperatures detected"
        else:
            report += f"\n✅ Temperatures within safe range"
        
        return report

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Stopping thermal monitor...")
    if 'monitor' in globals():
        monitor.stop_monitoring()
        print(monitor.get_thermal_report())
    sys.exit(0)

def main():
    """Main thermal monitoring function"""
    global monitor
    
    print("🌡️  MacBook Pro M3 Thermal Monitor for TTS Processing")
    print("=" * 60)
    print("Press Ctrl+C to stop monitoring and see report")
    
    # Set up signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and start monitor
    monitor = ThermalMonitor(max_temp=85, warning_temp=80)
    monitor.start_monitoring()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()