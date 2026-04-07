"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

UX Enhancement: System Health, Logs, and Performance Monitoring
Purpose: Monitor system health, view logs, track errors, and analyze performance
Requirements: UX-002 (Advanced Error Handling & Recovery), UX-005 (Comprehensive Feedback & Notifications)
"""

import streamlit as st
import os
import json
import time
import glob
import psutil
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Set page configuration
st.set_page_config(
    page_title="System Monitor - Dreamlet",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# UTILITY FUNCTIONS - UX_SYSTEM_MONITOR_v1.0.0 - Last updated: 2024-12-31
# ============================================================================

def get_logs_directory() -> str:
    """Get logs directory"""
    logs_dir = os.path.join(os.getcwd(), ".streamlit", "logs")
    ensure_directory_exists(logs_dir)
    return logs_dir

def get_metrics_directory() -> str:
    """Get metrics directory"""
    metrics_dir = os.path.join(os.getcwd(), ".streamlit", "metrics")
    ensure_directory_exists(metrics_dir)
    return metrics_dir

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def log_system_metrics() -> Dict:
    """Log current system metrics"""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Network metrics (if available)
        try:
            network = psutil.net_io_counters()
            network_stats = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        except:
            network_stats = {}
        
        # Process information
        try:
            current_process = psutil.Process()
            process_info = {
                "pid": current_process.pid,
                "memory_percent": current_process.memory_percent(),
                "cpu_percent": current_process.cpu_percent(),
                "num_threads": current_process.num_threads(),
                "create_time": current_process.create_time()
            }
        except:
            process_info = {}
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency": cpu_freq.current if cpu_freq else None
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": network_stats,
            "process": process_info
        }
        
        # Save metrics to file
        metrics_file = os.path.join(get_metrics_directory(), f"metrics_{datetime.now().strftime('%Y%m%d')}.json")
        
        # Load existing metrics or create new list
        if os.path.exists(metrics_file):
            with open(metrics_file, 'r') as f:
                all_metrics = json.load(f)
        else:
            all_metrics = []
        
        all_metrics.append(metrics)
        
        # Keep only last 1000 entries to prevent file from growing too large
        if len(all_metrics) > 1000:
            all_metrics = all_metrics[-1000:]
        
        with open(metrics_file, 'w') as f:
            json.dump(all_metrics, f, indent=2)
        
        return metrics
        
    except Exception as e:
        st.error(f"Failed to collect system metrics: {e}")
        return {}

def get_recent_metrics(hours: int = 24) -> List[Dict]:
    """Get recent system metrics"""
    metrics = []
    metrics_dir = get_metrics_directory()
    
    # Get metrics files from the last few days
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    for i in range(7):  # Check last 7 days
        date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
        metrics_file = os.path.join(metrics_dir, f"metrics_{date}.json")
        
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, 'r') as f:
                    daily_metrics = json.load(f)
                    
                # Filter by time
                for metric in daily_metrics:
                    metric_time = datetime.fromisoformat(metric['timestamp'])
                    if metric_time >= cutoff_time:
                        metrics.append(metric)
            except Exception as e:
                st.error(f"Failed to load metrics from {metrics_file}: {e}")
    
    # Sort by timestamp
    metrics.sort(key=lambda x: x['timestamp'])
    return metrics

def parse_log_file(file_path: str, max_lines: int = 1000) -> List[Dict]:
    """Parse log file and extract structured log entries"""
    log_entries = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # Take only the most recent lines
        lines = lines[-max_lines:]
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Try to parse different log formats
            log_entry = parse_log_line(line, line_num)
            if log_entry:
                log_entries.append(log_entry)
    
    except Exception as e:
        st.error(f"Failed to parse log file {file_path}: {e}")
    
    return log_entries

def parse_log_line(line: str, line_num: int) -> Optional[Dict]:
    """Parse a single log line"""
    # Common log patterns
    patterns = [
        # ISO timestamp format: 2024-01-01T12:00:00 [LEVEL] message
        r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*\[(\w+)\]\s*(.+)$',
        # Standard timestamp: 2024-01-01 12:00:00 LEVEL: message
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(\w+):\s*(.+)$',
        # Simple format: LEVEL: message
        r'^(\w+):\s*(.+)$',
        # Streamlit format
        r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+(.+)$'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            groups = match.groups()
            
            if len(groups) == 3:
                timestamp_str, level, message = groups
                try:
                    # Try to parse timestamp
                    if 'T' in timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except:
                    timestamp = datetime.now()
                
                return {
                    "line_number": line_num,
                    "timestamp": timestamp.isoformat(),
                    "level": level.upper(),
                    "message": message.strip(),
                    "raw_line": line
                }
            elif len(groups) == 2:
                if groups[0] in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
                    # Simple format
                    return {
                        "line_number": line_num,
                        "timestamp": datetime.now().isoformat(),
                        "level": groups[0].upper(),
                        "message": groups[1].strip(),
                        "raw_line": line
                    }
                else:
                    # Streamlit format
                    return {
                        "line_number": line_num,
                        "timestamp": groups[0],
                        "level": "INFO",
                        "message": groups[1].strip(),
                        "raw_line": line
                    }
    
    # If no pattern matches, return as generic info
    return {
        "line_number": line_num,
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "message": line,
        "raw_line": line
    }

def get_log_files() -> List[str]:
    """Get available log files"""
    log_files = []
    
    # Common log locations
    log_locations = [
        get_logs_directory(),
        os.path.join(os.getcwd(), "logs"),
        os.path.join(os.getcwd(), ".streamlit"),
        "/tmp",
        "/var/log"
    ]
    
    for location in log_locations:
        if os.path.exists(location):
            try:
                for file in os.listdir(location):
                    if file.endswith(('.log', '.txt')) or 'log' in file.lower():
                        full_path = os.path.join(location, file)
                        if os.path.isfile(full_path):
                            log_files.append(full_path)
            except PermissionError:
                continue
    
    return sorted(log_files)

def analyze_error_patterns(log_entries: List[Dict]) -> Dict:
    """Analyze error patterns in log entries"""
    error_analysis = {
        "total_errors": 0,
        "total_warnings": 0,
        "error_patterns": {},
        "recent_errors": [],
        "error_timeline": []
    }
    
    for entry in log_entries:
        level = entry.get("level", "INFO")
        message = entry.get("message", "")
        timestamp = entry.get("timestamp", "")
        
        if level == "ERROR":
            error_analysis["total_errors"] += 1
            error_analysis["recent_errors"].append(entry)
            
            # Extract error patterns
            # Simple pattern extraction - look for common error keywords
            error_keywords = ["failed", "error", "exception", "timeout", "connection", "permission", "not found"]
            for keyword in error_keywords:
                if keyword.lower() in message.lower():
                    if keyword not in error_analysis["error_patterns"]:
                        error_analysis["error_patterns"][keyword] = 0
                    error_analysis["error_patterns"][keyword] += 1
        
        elif level == "WARNING":
            error_analysis["total_warnings"] += 1
        
        # Add to timeline
        if level in ["ERROR", "WARNING"]:
            error_analysis["error_timeline"].append({
                "timestamp": timestamp,
                "level": level,
                "message": message[:100] + "..." if len(message) > 100 else message
            })
    
    # Keep only recent errors (last 50)
    error_analysis["recent_errors"] = error_analysis["recent_errors"][-50:]
    
    return error_analysis

def get_system_health_score() -> Tuple[int, List[str]]:
    """Calculate system health score and issues"""
    score = 100
    issues = []
    
    try:
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            score -= 20
            issues.append(f"High CPU usage: {cpu_percent:.1f}%")
        elif cpu_percent > 70:
            score -= 10
            issues.append(f"Moderate CPU usage: {cpu_percent:.1f}%")
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            score -= 25
            issues.append(f"High memory usage: {memory.percent:.1f}%")
        elif memory.percent > 75:
            score -= 15
            issues.append(f"Moderate memory usage: {memory.percent:.1f}%")
        
        # Check disk usage
        disk = psutil.disk_usage('/')
        if disk.percent > 95:
            score -= 30
            issues.append(f"Critical disk usage: {disk.percent:.1f}%")
        elif disk.percent > 85:
            score -= 15
            issues.append(f"High disk usage: {disk.percent:.1f}%")
        
        # Check for recent errors in logs
        log_files = get_log_files()
        recent_errors = 0
        
        for log_file in log_files[:3]:  # Check only first 3 log files
            try:
                log_entries = parse_log_file(log_file, max_lines=100)
                recent_errors += sum(1 for entry in log_entries if entry.get("level") == "ERROR")
            except:
                continue
        
        if recent_errors > 10:
            score -= 20
            issues.append(f"Many recent errors: {recent_errors}")
        elif recent_errors > 5:
            score -= 10
            issues.append(f"Some recent errors: {recent_errors}")
        
    except Exception as e:
        score -= 50
        issues.append(f"Failed to assess system health: {e}")
    
    return max(0, score), issues

def format_bytes(bytes_value: int) -> str:
    """Format bytes in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    """Render page header"""
    st.title("📊 System Monitor")
    st.markdown("*Monitor system health, view logs, and track performance metrics*")

def render_system_health():
    """Render system health overview"""
    st.subheader("🏥 System Health")
    
    # Get current metrics
    current_metrics = log_system_metrics()
    health_score, issues = get_system_health_score()
    
    # Health score display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Health score with color coding
        if health_score >= 80:
            color = "green"
            status = "Healthy"
        elif health_score >= 60:
            color = "orange"
            status = "Warning"
        else:
            color = "red"
            status = "Critical"
        
        st.metric("Health Score", f"{health_score}/100", delta=status)
        st.markdown(f"<div style='color: {color}'>● {status}</div>", unsafe_allow_html=True)
    
    with col2:
        cpu_percent = current_metrics.get("cpu", {}).get("percent", 0)
        st.metric("CPU Usage", f"{cpu_percent:.1f}%")
    
    with col3:
        memory_percent = current_metrics.get("memory", {}).get("percent", 0)
        st.metric("Memory Usage", f"{memory_percent:.1f}%")
    
    with col4:
        disk_percent = current_metrics.get("disk", {}).get("percent", 0)
        st.metric("Disk Usage", f"{disk_percent:.1f}%")
    
    # Issues display
    if issues:
        st.warning("**System Issues Detected:**")
        for issue in issues:
            st.write(f"⚠️ {issue}")
    else:
        st.success("✅ No system issues detected")

def render_performance_charts():
    """Render performance monitoring charts"""
    st.subheader("📈 Performance Metrics")
    
    # Get recent metrics
    hours = st.selectbox("Time Range", [1, 6, 12, 24, 48], index=3, key="metrics_hours")
    metrics = get_recent_metrics(hours)
    
    if not metrics:
        st.info("No performance data available. Metrics will be collected over time.")
        return
    
    # Prepare data for charts
    timestamps = [datetime.fromisoformat(m['timestamp']) for m in metrics]
    cpu_data = [m.get('cpu', {}).get('percent', 0) for m in metrics]
    memory_data = [m.get('memory', {}).get('percent', 0) for m in metrics]
    disk_data = [m.get('disk', {}).get('percent', 0) for m in metrics]
    
    # Create charts
    tab1, tab2, tab3 = st.tabs(["CPU & Memory", "Disk Usage", "Detailed Metrics"])
    
    with tab1:
        # CPU and Memory chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=cpu_data,
            mode='lines',
            name='CPU %',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=memory_data,
            mode='lines',
            name='Memory %',
            line=dict(color='red')
        ))
        
        fig.update_layout(
            title="CPU and Memory Usage Over Time",
            xaxis_title="Time",
            yaxis_title="Usage %",
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        # Disk usage chart
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=disk_data,
            mode='lines',
            name='Disk %',
            line=dict(color='green'),
            fill='tonexty'
        ))
        
        fig.update_layout(
            title="Disk Usage Over Time",
            xaxis_title="Time",
            yaxis_title="Usage %",
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Detailed metrics table
        if metrics:
            latest_metric = metrics[-1]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**CPU Information:**")
                cpu_info = latest_metric.get('cpu', {})
                st.write(f"- Usage: {cpu_info.get('percent', 0):.1f}%")
                st.write(f"- Cores: {cpu_info.get('count', 'Unknown')}")
                st.write(f"- Frequency: {cpu_info.get('frequency', 'Unknown')} MHz")
                
                st.write("**Memory Information:**")
                memory_info = latest_metric.get('memory', {})
                st.write(f"- Usage: {memory_info.get('percent', 0):.1f}%")
                st.write(f"- Total: {format_bytes(memory_info.get('total', 0))}")
                st.write(f"- Available: {format_bytes(memory_info.get('available', 0))}")
                st.write(f"- Used: {format_bytes(memory_info.get('used', 0))}")
            
            with col2:
                st.write("**Disk Information:**")
                disk_info = latest_metric.get('disk', {})
                st.write(f"- Usage: {disk_info.get('percent', 0):.1f}%")
                st.write(f"- Total: {format_bytes(disk_info.get('total', 0))}")
                st.write(f"- Used: {format_bytes(disk_info.get('used', 0))}")
                st.write(f"- Free: {format_bytes(disk_info.get('free', 0))}")
                
                st.write("**Process Information:**")
                process_info = latest_metric.get('process', {})
                st.write(f"- PID: {process_info.get('pid', 'Unknown')}")
                st.write(f"- Memory: {process_info.get('memory_percent', 0):.1f}%")
                st.write(f"- CPU: {process_info.get('cpu_percent', 0):.1f}%")
                st.write(f"- Threads: {process_info.get('num_threads', 'Unknown')}")

def render_log_viewer():
    """Render log file viewer"""
    st.subheader("📋 Log Viewer")
    
    log_files = get_log_files()
    
    if not log_files:
        st.info("No log files found.")
        return
    
    # File selection
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        selected_log = st.selectbox("Select Log File", log_files, key="selected_log_file")
    
    with col2:
        max_lines = st.number_input("Max Lines", min_value=100, max_value=10000, value=1000, step=100)
    
    with col3:
        auto_refresh = st.checkbox("Auto Refresh", value=False)
    
    if selected_log:
        # Parse log file
        with st.spinner("Loading log file..."):
            log_entries = parse_log_file(selected_log, max_lines)
        
        if not log_entries:
            st.warning("No log entries found or unable to parse log file.")
            return
        
        # Log level filter
        available_levels = list(set(entry.get("level", "INFO") for entry in log_entries))
        selected_levels = st.multiselect("Filter by Level", available_levels, default=available_levels)
        
        # Search filter
        search_term = st.text_input("Search in logs", key="log_search")
        
        # Filter log entries
        filtered_entries = []
        for entry in log_entries:
            if entry.get("level") in selected_levels:
                if not search_term or search_term.lower() in entry.get("message", "").lower():
                    filtered_entries.append(entry)
        
        # Display log entries
        st.write(f"**Showing {len(filtered_entries)} of {len(log_entries)} log entries**")
        
        # Create DataFrame for better display
        if filtered_entries:
            df_data = []
            for entry in filtered_entries[-100:]:  # Show last 100 entries
                df_data.append({
                    "Timestamp": entry.get("timestamp", ""),
                    "Level": entry.get("level", ""),
                    "Message": entry.get("message", "")[:200] + ("..." if len(entry.get("message", "")) > 200 else "")
                })
            
            df = pd.DataFrame(df_data)
            
            # Color code by level
            def color_level(val):
                if val == "ERROR":
                    return "background-color: #ffebee"
                elif val == "WARNING":
                    return "background-color: #fff3e0"
                elif val == "INFO":
                    return "background-color: #e8f5e8"
                return ""
            
            styled_df = df.style.applymap(color_level, subset=['Level'])
            st.dataframe(styled_df, use_container_width=True, height=400)
            
            # Export logs
            if st.button("Export Filtered Logs"):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        # Auto refresh
        if auto_refresh:
            time.sleep(5)
            st.rerun()

def render_error_analysis():
    """Render error analysis dashboard"""
    st.subheader("🚨 Error Analysis")
    
    log_files = get_log_files()
    
    if not log_files:
        st.info("No log files available for error analysis.")
        return
    
    # Analyze errors from all log files
    all_log_entries = []
    
    with st.spinner("Analyzing errors across all log files..."):
        for log_file in log_files[:5]:  # Analyze first 5 log files
            try:
                entries = parse_log_file(log_file, max_lines=500)
                all_log_entries.extend(entries)
            except Exception as e:
                st.warning(f"Could not analyze {log_file}: {e}")
    
    if not all_log_entries:
        st.warning("No log entries found for analysis.")
        return
    
    # Perform error analysis
    error_analysis = analyze_error_patterns(all_log_entries)
    
    # Display error summary
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Errors", error_analysis["total_errors"])
    
    with col2:
        st.metric("Total Warnings", error_analysis["total_warnings"])
    
    with col3:
        total_entries = len(all_log_entries)
        error_rate = (error_analysis["total_errors"] / total_entries * 100) if total_entries > 0 else 0
        st.metric("Error Rate", f"{error_rate:.1f}%")
    
    with col4:
        unique_patterns = len(error_analysis["error_patterns"])
        st.metric("Error Patterns", unique_patterns)
    
    # Error patterns chart
    if error_analysis["error_patterns"]:
        st.write("**Common Error Patterns:**")
        
        patterns_df = pd.DataFrame(
            list(error_analysis["error_patterns"].items()),
            columns=["Pattern", "Count"]
        ).sort_values("Count", ascending=False)
        
        fig = px.bar(patterns_df, x="Pattern", y="Count", title="Most Common Error Patterns")
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent errors
    if error_analysis["recent_errors"]:
        st.write("**Recent Errors:**")
        
        for error in error_analysis["recent_errors"][-10:]:  # Show last 10 errors
            with st.expander(f"Error at {error.get('timestamp', 'Unknown time')}"):
                st.code(error.get("message", "No message"), language="text")
    
    # Error timeline
    if error_analysis["error_timeline"]:
        st.write("**Error Timeline:**")
        
        timeline_df = pd.DataFrame(error_analysis["error_timeline"])
        if not timeline_df.empty:
            timeline_df['timestamp'] = pd.to_datetime(timeline_df['timestamp'])
            
            # Group by hour and count
            timeline_df['hour'] = timeline_df['timestamp'].dt.floor('H')
            hourly_errors = timeline_df.groupby(['hour', 'level']).size().reset_index(name='count')
            
            fig = px.bar(hourly_errors, x='hour', y='count', color='level', 
                        title="Error Timeline (by Hour)")
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application function"""
    render_header()
    
    # Auto-refresh option
    col1, col2 = st.columns([4, 1])
    with col2:
        auto_refresh = st.checkbox("Auto Refresh (30s)", value=False)
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["System Health", "Performance", "Log Viewer", "Error Analysis"])
    
    with tab1:
        render_system_health()
    
    with tab2:
        render_performance_charts()
    
    with tab3:
        render_log_viewer()
    
    with tab4:
        render_error_analysis()
    
    # Auto refresh
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(f"*System Monitor v1.0.0 | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

if __name__ == "__main__":
    main()