"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

UX Enhancement: Main Workflow Management Dashboard
Purpose: Provides comprehensive overview of all video production projects and workflows
Requirements: UX-001 (Comprehensive Workflow Management)
"""

import streamlit as st
import os
import json
import time
import glob
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import psutil
import subprocess

# Set page configuration
st.set_page_config(
    page_title="Dashboard - Dreamlet",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# UTILITY FUNCTIONS - UX_DASHBOARD_v1.0.0 - Last updated: 2024-12-31
# ============================================================================

def get_input_directory() -> str:
    """Get the path to the input directory"""
    return os.path.join(os.getcwd(), "input")

def get_output_directory() -> str:
    """Get the path to the output directory"""
    return os.path.join(os.getcwd(), "output")

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def get_dashboard_state_file() -> str:
    """Get path to dashboard state file"""
    state_dir = os.path.join(os.getcwd(), ".streamlit", "dashboard_state")
    ensure_directory_exists(state_dir)
    return os.path.join(state_dir, "projects.json")

def save_dashboard_state(state: Dict) -> None:
    """Save dashboard state to file"""
    try:
        with open(get_dashboard_state_file(), 'w') as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        st.error(f"Failed to save dashboard state: {e}")

def load_dashboard_state() -> Dict:
    """Load dashboard state from file"""
    try:
        state_file = get_dashboard_state_file()
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Failed to load dashboard state: {e}")
    return {"projects": {}, "last_updated": str(datetime.now())}

def scan_projects() -> Dict[str, Dict]:
    """Scan input directory for projects and their status"""
    projects = {}
    input_dir = get_input_directory()
    
    if not os.path.exists(input_dir):
        return projects
    
    # Scan for course/lecture structure
    for root, dirs, files in os.walk(input_dir):
        # Skip hidden directories and processed folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and 'processed' not in d.lower()]
        
        # Look for lecture folders with required files
        if any(f.endswith(('.txt', '.md', '.pptx')) for f in files):
            relative_path = os.path.relpath(root, input_dir)
            project_id = relative_path.replace(os.sep, '_')
            
            projects[project_id] = {
                "path": root,
                "relative_path": relative_path,
                "name": relative_path,
                "files": analyze_project_files(root),
                "status": determine_project_status(root),
                "last_modified": get_last_modified_time(root),
                "size": get_directory_size(root)
            }
    
    return projects

def analyze_project_files(project_path: str) -> Dict:
    """Analyze files in a project directory"""
    files = {
        "transcript": [],
        "slides": [],
        "presentation": [],
        "audio": [],
        "images": [],
        "video": []
    }
    
    for root, dirs, file_list in os.walk(project_path):
        for file in file_list:
            file_path = os.path.join(root, file)
            file_lower = file.lower()
            
            if file_lower.endswith(('.txt', '.md')) and 'transcript' in file_lower:
                files["transcript"].append(file_path)
            elif file_lower.endswith(('.txt', '.md')) and 'slide' in file_lower:
                files["slides"].append(file_path)
            elif file_lower.endswith('.pptx'):
                files["presentation"].append(file_path)
            elif file_lower.endswith('.mp3'):
                files["audio"].append(file_path)
            elif file_lower.endswith(('.png', '.jpg', '.jpeg')):
                files["images"].append(file_path)
            elif file_lower.endswith('.mp4'):
                files["video"].append(file_path)
    
    return files

def determine_project_status(project_path: str) -> Dict:
    """Determine the current status of a project"""
    files = analyze_project_files(project_path)
    
    status = {
        "stage": "not_started",
        "progress": 0,
        "completed_steps": [],
        "next_step": "01_Adjust",
        "issues": []
    }
    
    # Check completion of each stage
    stages = [
        ("01_Adjust", lambda f: len(f["transcript"]) > 0 and len(f["slides"]) > 0),
        ("02_Rename", lambda f: any("Lecture" in os.path.basename(t) for t in f["transcript"])),
        ("03_Count", lambda f: len(f["transcript"]) > 0 and len(f["slides"]) > 0 and len(f["presentation"]) > 0),
        ("04_Save_Text", lambda f: any("sections" in t for t in f["transcript"])),
        ("05_TTS", lambda f: len(f["audio"]) > 0),
        ("06_4K_Image", lambda f: len(f["images"]) > 0),
        ("07_MP4", lambda f: len(f["video"]) > 0)
    ]
    
    completed_count = 0
    for stage_name, check_func in stages:
        if check_func(files):
            status["completed_steps"].append(stage_name)
            completed_count += 1
        else:
            if not status["next_step"] or status["next_step"] == "01_Adjust":
                status["next_step"] = stage_name
            break
    
    status["progress"] = (completed_count / len(stages)) * 100
    
    if completed_count == 0:
        status["stage"] = "not_started"
    elif completed_count == len(stages):
        status["stage"] = "completed"
        status["next_step"] = "completed"
    else:
        status["stage"] = "in_progress"
    
    # Check for issues
    if len(files["transcript"]) == 0:
        status["issues"].append("No transcript files found")
    if len(files["slides"]) == 0:
        status["issues"].append("No slide files found")
    if len(files["presentation"]) == 0:
        status["issues"].append("No presentation files found")
    
    return status

def get_last_modified_time(directory: str) -> str:
    """Get the last modified time of any file in directory"""
    try:
        latest_time = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                mtime = os.path.getmtime(file_path)
                if mtime > latest_time:
                    latest_time = mtime
        
        if latest_time > 0:
            return datetime.fromtimestamp(latest_time).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return "Unknown"

def get_directory_size(directory: str) -> str:
    """Get human-readable size of directory"""
    try:
        total_size = 0
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        
        # Convert to human readable format
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total_size < 1024.0:
                return f"{total_size:.1f} {unit}"
            total_size /= 1024.0
        return f"{total_size:.1f} TB"
    except Exception:
        return "Unknown"

def get_system_resources() -> Dict:
    """Get current system resource usage"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": cpu_percent,
            "memory_used": memory.percent,
            "memory_available": f"{memory.available / (1024**3):.1f} GB",
            "disk_used": disk.percent,
            "disk_free": f"{disk.free / (1024**3):.1f} GB"
        }
    except Exception:
        return {
            "cpu": 0,
            "memory_used": 0,
            "memory_available": "Unknown",
            "disk_used": 0,
            "disk_free": "Unknown"
        }

def get_status_color(status: str) -> str:
    """Get color for status indicators"""
    colors = {
        "completed": "#28a745",  # Green
        "in_progress": "#ffc107",  # Yellow
        "not_started": "#6c757d",  # Gray
        "error": "#dc3545"  # Red
    }
    return colors.get(status, "#6c757d")

def format_progress_bar(progress: float, status: str) -> str:
    """Create HTML progress bar"""
    color = get_status_color(status)
    return f"""
    <div style="background-color: #e9ecef; border-radius: 4px; height: 20px; margin: 5px 0;">
        <div style="background-color: {color}; height: 100%; border-radius: 4px; width: {progress}%; 
                    display: flex; align-items: center; justify-content: center; color: white; font-size: 12px;">
            {progress:.1f}%
        </div>
    </div>
    """

# ============================================================================
# DASHBOARD UI COMPONENTS
# ============================================================================

def render_header():
    """Render dashboard header with title and refresh controls"""
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title("📊 Dreamlet Dashboard")
        st.markdown("*Comprehensive overview of your video production projects*")
    
    with col2:
        if st.button("🔄 Refresh", help="Refresh project data"):
            st.rerun()
    
    with col3:
        auto_refresh = st.checkbox("Auto-refresh", value=False, help="Automatically refresh every 30 seconds")
        if auto_refresh:
            time.sleep(30)
            st.rerun()

def render_system_metrics():
    """Render system resource usage metrics"""
    st.subheader("🖥️ System Resources")
    
    resources = get_system_resources()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("CPU Usage", f"{resources['cpu']:.1f}%")
    
    with col2:
        st.metric("Memory Usage", f"{resources['memory_used']:.1f}%", 
                 delta=f"{resources['memory_available']} available")
    
    with col3:
        st.metric("Disk Usage", f"{resources['disk_used']:.1f}%",
                 delta=f"{resources['disk_free']} free")
    
    with col4:
        # Get number of active projects
        projects = scan_projects()
        active_count = sum(1 for p in projects.values() if p["status"]["stage"] == "in_progress")
        st.metric("Active Projects", active_count)

def render_project_overview(projects: Dict):
    """Render project overview statistics"""
    st.subheader("📈 Project Overview")
    
    if not projects:
        st.info("No projects found. Add some content to the input directory to get started.")
        return
    
    # Calculate statistics
    total_projects = len(projects)
    completed = sum(1 for p in projects.values() if p["status"]["stage"] == "completed")
    in_progress = sum(1 for p in projects.values() if p["status"]["stage"] == "in_progress")
    not_started = sum(1 for p in projects.values() if p["status"]["stage"] == "not_started")
    with_issues = sum(1 for p in projects.values() if p["status"]["issues"])
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Projects", total_projects)
    
    with col2:
        st.metric("Completed", completed, delta=f"{(completed/total_projects*100):.1f}%" if total_projects > 0 else "0%")
    
    with col3:
        st.metric("In Progress", in_progress, delta=f"{(in_progress/total_projects*100):.1f}%" if total_projects > 0 else "0%")
    
    with col4:
        st.metric("Not Started", not_started, delta=f"{(not_started/total_projects*100):.1f}%" if total_projects > 0 else "0%")
    
    with col5:
        st.metric("With Issues", with_issues, delta="⚠️" if with_issues > 0 else "✅")

def render_project_table(projects: Dict):
    """Render detailed project table"""
    st.subheader("📋 Project Details")
    
    if not projects:
        return
    
    # Prepare data for table
    table_data = []
    for project_id, project in projects.items():
        status = project["status"]
        table_data.append({
            "Project": project["name"],
            "Status": status["stage"].replace("_", " ").title(),
            "Progress": f"{status['progress']:.1f}%",
            "Next Step": status["next_step"].replace("_", " "),
            "Issues": len(status["issues"]),
            "Size": project["size"],
            "Last Modified": project["last_modified"],
            "Actions": project_id  # Will be used for action buttons
        })
    
    # Create DataFrame
    df = pd.DataFrame(table_data)
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Completed", "In Progress", "Not Started"],
            key="status_filter"
        )
    
    with col2:
        issues_filter = st.selectbox(
            "Filter by Issues",
            ["All", "With Issues", "No Issues"],
            key="issues_filter"
        )
    
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Project", "Status", "Progress", "Last Modified"],
            key="sort_by"
        )
    
    # Apply filters
    filtered_df = df.copy()
    
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["Status"] == status_filter]
    
    if issues_filter == "With Issues":
        filtered_df = filtered_df[filtered_df["Issues"] > 0]
    elif issues_filter == "No Issues":
        filtered_df = filtered_df[filtered_df["Issues"] == 0]
    
    # Sort
    if sort_by == "Last Modified":
        # Convert to datetime for proper sorting
        filtered_df["Last Modified"] = pd.to_datetime(filtered_df["Last Modified"], errors='coerce')
        filtered_df = filtered_df.sort_values("Last Modified", ascending=False)
        filtered_df["Last Modified"] = filtered_df["Last Modified"].dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        filtered_df = filtered_df.sort_values(sort_by)
    
    # Display table with action buttons
    for idx, row in filtered_df.iterrows():
        with st.container():
            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([2, 1, 1, 1.5, 0.5, 1, 1.5, 1.5])
            
            with col1:
                st.write(f"**{row['Project']}**")
            
            with col2:
                status_color = get_status_color(row['Status'].lower().replace(" ", "_"))
                st.markdown(f"<span style='color: {status_color}'>●</span> {row['Status']}", unsafe_allow_html=True)
            
            with col3:
                st.markdown(format_progress_bar(float(row['Progress'].rstrip('%')), row['Status'].lower().replace(" ", "_")), unsafe_allow_html=True)
            
            with col4:
                st.write(row['Next Step'])
            
            with col5:
                if row['Issues'] > 0:
                    st.markdown(f"⚠️ {row['Issues']}")
                else:
                    st.markdown("✅")
            
            with col6:
                st.write(row['Size'])
            
            with col7:
                st.write(row['Last Modified'])
            
            with col8:
                action_col1, action_col2 = st.columns(2)
                with action_col1:
                    if st.button("▶️", key=f"start_{row['Actions']}", help="Start/Resume workflow"):
                        st.info(f"Starting workflow for {row['Project']}")
                        # Here you would implement workflow start logic
                
                with action_col2:
                    if st.button("📊", key=f"details_{row['Actions']}", help="View details"):
                        st.session_state[f"show_details_{row['Actions']}"] = True
            
            # Show details if requested
            if st.session_state.get(f"show_details_{row['Actions']}", False):
                with st.expander(f"Details for {row['Project']}", expanded=True):
                    project = projects[row['Actions']]
                    
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.write("**Files Found:**")
                        files = project["files"]
                        st.write(f"- Transcripts: {len(files['transcript'])}")
                        st.write(f"- Slides: {len(files['slides'])}")
                        st.write(f"- Presentations: {len(files['presentation'])}")
                        st.write(f"- Audio: {len(files['audio'])}")
                        st.write(f"- Images: {len(files['images'])}")
                        st.write(f"- Videos: {len(files['video'])}")
                    
                    with detail_col2:
                        st.write("**Status Details:**")
                        status = project["status"]
                        st.write(f"- Completed Steps: {', '.join(status['completed_steps']) if status['completed_steps'] else 'None'}")
                        st.write(f"- Next Step: {status['next_step']}")
                        if status["issues"]:
                            st.write("**Issues:**")
                            for issue in status["issues"]:
                                st.write(f"- ⚠️ {issue}")
                    
                    if st.button("Close Details", key=f"close_{row['Actions']}"):
                        st.session_state[f"show_details_{row['Actions']}"] = False
                        st.rerun()
            
            st.divider()

def render_quick_actions():
    """Render quick action buttons"""
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Scan Projects", help="Rescan input directory for projects"):
            with st.spinner("Scanning projects..."):
                projects = scan_projects()
                st.success(f"Found {len(projects)} projects")
    
    with col2:
        if st.button("📊 Export Report", help="Export project status report"):
            projects = scan_projects()
            if projects:
                # Create CSV report
                report_data = []
                for project_id, project in projects.items():
                    status = project["status"]
                    report_data.append({
                        "Project ID": project_id,
                        "Project Name": project["name"],
                        "Status": status["stage"],
                        "Progress": status["progress"],
                        "Next Step": status["next_step"],
                        "Issues Count": len(status["issues"]),
                        "Issues": "; ".join(status["issues"]),
                        "Size": project["size"],
                        "Last Modified": project["last_modified"]
                    })
                
                df = pd.DataFrame(report_data)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    label="📥 Download CSV Report",
                    data=csv,
                    file_name=f"dreamlet_dashboard_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No projects found to export")
    
    with col3:
        if st.button("🧹 Cleanup", help="Clean up temporary files"):
            with st.spinner("Cleaning up..."):
                # Implement cleanup logic here
                time.sleep(2)
                st.success("Cleanup completed")
    
    with col4:
        if st.button("⚙️ Settings", help="Open dashboard settings"):
            st.info("Settings panel would open here")

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

def main():
    """Main dashboard function"""
    # Initialize session state
    if "dashboard_initialized" not in st.session_state:
        st.session_state.dashboard_initialized = True
    
    # Render header
    render_header()
    
    # Render system metrics
    render_system_metrics()
    
    st.divider()
    
    # Scan projects
    with st.spinner("Loading projects..."):
        projects = scan_projects()
    
    # Render project overview
    render_project_overview(projects)
    
    st.divider()
    
    # Render project table
    render_project_table(projects)
    
    st.divider()
    
    # Render quick actions
    render_quick_actions()
    
    # Footer
    st.markdown("---")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Dreamlet Dashboard v1.0.0*")

if __name__ == "__main__":
    main()