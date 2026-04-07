#!/usr/bin/env python3
"""
No-Sudo Thermal Monitor for MacBook Pro M3
Uses alternative methods to monitor system load without requiring password
"""

import subprocess
import time
import threading
import signal
import sys
import psutil
from datetime import datetime

class NoSudoThermalMonitor:
    def __init__(self, max_cpu_percent=85, warning_cpu_percent=75):
        self.max_cpu_percent = max_cpu_percent
        self.warning_cpu_percent = warning_cpu_percent
        self.monitoring = False
        self.current_cpu = None
        self.cpu_history = []
        
    def get_system_metrics(self):
        """Get system metrics without sudo"""
        try:
            # CPU usage percentage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # CPU frequency (if available)
            try:
                cpu_freq = psutil.cpu_freq()
                freq_current = cpu_freq.current if cpu_freq else None
            except:
                freq_current = None
            
            # Process count
            process_count = len(psutil.pids())
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'cpu_freq_mhz': freq_current,
                'process_count': process_count,
                'timestamp': datetime.now()
            }
        except Exception as e:
            print(f"Error getting metrics: {e}")
            return None
    
    def estimate_thermal_load(self, metrics):
        """Estimate thermal load based on available metrics"""
        if not metrics:
            return None
            
        # Thermal load estimation based on:
        # - CPU usage (primary factor)
        # - Memory pressure (secondary)
        # - Process count (tertiary)
        
        cpu_factor = metrics['cpu_percent']
        memory_factor = metrics['memory_percent'] * 0.3  # Less impact
        process_factor = min(metrics['process_count'] / 500 * 10, 20)  # Cap at 20%
        
        estimated_thermal_load = cpu_factor + memory_factor + process_factor
        return min(estimated_thermal_load, 100)  # Cap at 100%
    
    def monitor_loop(self):
        """Continuous system monitoring"""
        while self.monitoring:
            metrics = self.get_system_metrics()
            if metrics:
                thermal_load = self.estimate_thermal_load(metrics)
                
                self.current_cpu = metrics['cpu_percent']
                self.cpu_history.append({
                    'time': metrics['timestamp'],
                    'cpu_percent': metrics['cpu_percent'],
                    'thermal_load': thermal_load,
                    'memory_percent': metrics['memory_percent']
                })
                
                # Keep only last 60 readings (10 minutes at 10s intervals)
                if len(self.cpu_history) > 60:
                    self.cpu_history.pop(0)
                
                # System load warnings
                if thermal_load >= self.max_cpu_percent:
                    print(f"\n🚨 HIGH LOAD: CPU {metrics['cpu_percent']:.1f}% (Thermal Load: {thermal_load:.1f}%) - Consider pausing!")
                elif thermal_load >= self.warning_cpu_percent:
                    print(f"\n⚠️  MODERATE LOAD: CPU {metrics['cpu_percent']:.1f}% (Thermal Load: {thermal_load:.1f}%)")
                else:
                    # Show periodic updates
                    if len(self.cpu_history) % 6 == 0:  # Every minute
                        print(f"✅ CPU: {metrics['cpu_percent']:.1f}% | RAM: {metrics['memory_percent']:.1f}% | Load: {thermal_load:.1f}%")
                
            time.sleep(10)  # Check every 10 seconds
    
    def start_monitoring(self):
        """Start system monitoring in background"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print(f"📊 System load monitoring started (warning: {self.warning_cpu_percent}%, max: {self.max_cpu_percent}%)")
        print("💡 Monitoring CPU usage as thermal proxy (no password required)")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1)
        print("🛑 System monitoring stopped")
    
    def get_performance_report(self):
        """Generate system performance report"""
        if not self.cpu_history:
            return "No performance data collected"
        
        cpu_values = [reading['cpu_percent'] for reading in self.cpu_history]
        thermal_values = [reading['thermal_load'] for reading in self.cpu_history]
        memory_values = [reading['memory_percent'] for reading in self.cpu_history]
        
        avg_cpu = sum(cpu_values) / len(cpu_values)
        max_cpu = max(cpu_values)
        avg_thermal = sum(thermal_values) / len(thermal_values)
        max_thermal = max(thermal_values)
        avg_memory = sum(memory_values) / len(memory_values)
        
        report = f"""
📊 System Performance Report:
   Average CPU Usage: {avg_cpu:.1f}%
   Maximum CPU Usage: {max_cpu:.1f}%
   Average Thermal Load: {avg_thermal:.1f}%
   Maximum Thermal Load: {max_thermal:.1f}%
   Average Memory Usage: {avg_memory:.1f}%
   Readings Collected: {len(cpu_values)}
   Monitoring Duration: {len(cpu_values) * 10 / 60:.1f} minutes
        """
        
        if max_thermal >= self.max_cpu_percent:
            report += f"\n🚨 HIGH system load detected!"
        elif max_thermal >= self.warning_cpu_percent:
            report += f"\n⚠️  Moderate system load detected"
        else:
            report += f"\n✅ System load within acceptable range"
        
        return report

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Stopping system monitor...")
    if 'monitor' in globals():
        monitor.stop_monitoring()
        print(monitor.get_performance_report())
    sys.exit(0)

def main():
    """Main system monitoring function"""
    global monitor
    
    print("📊 MacBook Pro M3 System Monitor (No Password Required)")
    print("=" * 60)
    print("Monitoring CPU usage as thermal proxy")
    print("Press Ctrl+C to stop monitoring and see report")
    
    # Set up signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and start monitor
    monitor = NoSudoThermalMonitor(max_cpu_percent=85, warning_cpu_percent=75)
    monitor.start_monitoring()
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()