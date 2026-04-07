"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent

UX Enhancement: User Preferences, Notifications, and Help System
Purpose: Manage user preferences, configure notifications, provide help and onboarding
Requirements: UX-004 (Improved Navigation & Usability), UX-005 (Comprehensive Feedback & Notifications)
"""

import streamlit as st
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Set page configuration
st.set_page_config(
    page_title="User Settings - Dreamlet",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# UTILITY FUNCTIONS - UX_USER_SETTINGS_v1.0.0 - Last updated: 2024-12-31
# ============================================================================

def get_settings_directory() -> str:
    """Get user settings directory"""
    settings_dir = os.path.join(os.getcwd(), ".streamlit", "user_settings")
    ensure_directory_exists(settings_dir)
    return settings_dir

def get_help_directory() -> str:
    """Get help content directory"""
    help_dir = os.path.join(os.getcwd(), ".streamlit", "help_content")
    ensure_directory_exists(help_dir)
    return help_dir

def ensure_directory_exists(directory_path: str) -> None:
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

def get_default_settings() -> Dict:
    """Get default user settings"""
    return {
        "general": {
            "theme": "light",
            "auto_refresh": False,
            "auto_refresh_interval": 30,
            "show_tooltips": True,
            "compact_mode": False,
            "language": "en"
        },
        "notifications": {
            "enabled": True,
            "browser_notifications": True,
            "email_notifications": False,
            "email_address": "",
            "notify_on_completion": True,
            "notify_on_errors": True,
            "notify_on_warnings": False,
            "sound_enabled": True
        },
        "workflow": {
            "auto_save_checkpoints": True,
            "checkpoint_interval": 300,  # seconds
            "auto_retry_failed_steps": True,
            "max_retry_attempts": 3,
            "pause_on_errors": True,
            "show_progress_details": True
        },
        "performance": {
            "max_concurrent_processes": 2,
            "memory_limit_mb": 4096,
            "temp_file_cleanup": True,
            "cache_enabled": True,
            "log_level": "INFO"
        },
        "ui": {
            "sidebar_collapsed": False,
            "show_system_metrics": True,
            "show_quick_actions": True,
            "table_page_size": 25,
            "chart_animation": True
        },
        "keyboard_shortcuts": {
            "refresh": "F5",
            "dashboard": "Ctrl+D",
            "workflow": "Ctrl+W",
            "logs": "Ctrl+L",
            "settings": "Ctrl+,",
            "help": "F1"
        },
        "onboarding": {
            "completed": False,
            "current_step": 0,
            "skip_intro": False,
            "show_tips": True
        }
    }

def load_user_settings() -> Dict:
    """Load user settings from file"""
    settings_file = os.path.join(get_settings_directory(), "user_settings.json")
    
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                saved_settings = json.load(f)
            
            # Merge with defaults to ensure all keys exist
            default_settings = get_default_settings()
            merged_settings = merge_settings(default_settings, saved_settings)
            return merged_settings
    except Exception as e:
        st.error(f"Failed to load user settings: {e}")
    
    return get_default_settings()

def save_user_settings(settings: Dict) -> None:
    """Save user settings to file"""
    settings_file = os.path.join(get_settings_directory(), "user_settings.json")
    
    try:
        settings["last_updated"] = datetime.now().isoformat()
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save user settings: {e}")

def merge_settings(default: Dict, saved: Dict) -> Dict:
    """Recursively merge saved settings with defaults"""
    result = default.copy()
    
    for key, value in saved.items():
        if key in result:
            if isinstance(value, dict) and isinstance(result[key], dict):
                result[key] = merge_settings(result[key], value)
            else:
                result[key] = value
        else:
            result[key] = value
    
    return result

def export_settings(settings: Dict) -> str:
    """Export settings as JSON string"""
    export_data = {
        "dreamlet_settings": settings,
        "export_date": datetime.now().isoformat(),
        "version": "1.0.0"
    }
    return json.dumps(export_data, indent=2)

def import_settings(settings_json: str) -> Tuple[bool, str, Dict]:
    """Import settings from JSON string"""
    try:
        import_data = json.loads(settings_json)
        
        if "dreamlet_settings" not in import_data:
            return False, "Invalid settings file format", {}
        
        imported_settings = import_data["dreamlet_settings"]
        
        # Validate settings structure
        default_settings = get_default_settings()
        merged_settings = merge_settings(default_settings, imported_settings)
        
        return True, "Settings imported successfully", merged_settings
        
    except json.JSONDecodeError:
        return False, "Invalid JSON format", {}
    except Exception as e:
        return False, f"Import failed: {str(e)}", {}

def get_help_content() -> Dict:
    """Get help content for the application"""
    return {
        "getting_started": {
            "title": "Getting Started with Dreamlet",
            "content": """
            Welcome to Dreamlet Educational Video Production System! This guide will help you get started.
            
            ## Overview
            Dreamlet automates the creation of educational videos from transcript files, slide descriptions, and PowerPoint presentations.
            
            ## Basic Workflow
            1. **Prepare your content**: Create transcript files, slide descriptions, and PowerPoint presentations
            2. **Organize files**: Place them in the input directory following the expected structure
            3. **Process step by step**: Use pages 01-10 to process your content through the pipeline
            4. **Monitor progress**: Use the Dashboard to track your projects
            
            ## File Structure
            ```
            input/
            ├── course_01/
            │   ├── lecture_01/
            │   │   ├── transcript.txt
            │   │   ├── slides.txt
            │   │   └── presentation.pptx
            │   └── lecture_02/
            └── course_02/
            ```
            
            ## Next Steps
            - Visit the Dashboard to see your projects
            - Use the Workflow Manager to automate processing
            - Check System Monitor for performance insights
            """
        },
        "workflow_steps": {
            "title": "Understanding Workflow Steps",
            "content": """
            ## Processing Steps Overview
            
            ### 01 - Adjust AAA EEE
            Make necessary adjustments to transcript and slide files to ensure consistency.
            
            ### 02 - Rename
            Fix incorrectly named files according to standard naming conventions.
            
            ### 03 - Count
            Verify alignment between transcript sections, slide descriptions, and presentation slides.
            
            ### 04 - Save Text
            Break transcript files into individual sections for TTS processing.
            
            ### 05 - TTS (Text-to-Speech)
            Convert transcript sections to MP3 audio files using OpenAI's TTS API.
            
            ### 06 - 4K Image
            Generate high-resolution images from presentation slides.
            
            ### 07 - MP4
            Combine audio and images to create final educational videos.
            
            ### 08 - Multilingual Text
            Handle multilingual text processing for international content.
            
            ### 09 - Multilingual TTS
            Handle multilingual text-to-speech processing.
            
            ### 10 - MP4 GPU
            GPU-accelerated video processing for better performance.
            """
        },
        "troubleshooting": {
            "title": "Troubleshooting Common Issues",
            "content": """
            ## Common Issues and Solutions
            
            ### Files Not Found
            - Ensure files are in the correct input directory structure
            - Check file naming conventions (use the Rename page to fix)
            - Verify file permissions
            
            ### Processing Errors
            - Check the System Monitor for detailed error logs
            - Ensure you have sufficient disk space
            - Verify API keys are configured correctly
            
            ### Performance Issues
            - Monitor system resources in System Monitor
            - Reduce concurrent processes in settings
            - Clear temporary files regularly
            
            ### Audio/Video Issues
            - Ensure FFmpeg is properly installed
            - Check audio file formats are supported
            - Verify image resolution requirements
            
            ### API Errors
            - Check OpenAI API key configuration
            - Monitor API usage limits
            - Verify network connectivity
            """
        },
        "keyboard_shortcuts": {
            "title": "Keyboard Shortcuts",
            "content": """
            ## Available Keyboard Shortcuts
            
            ### Navigation
            - **F5**: Refresh current page
            - **Ctrl+D**: Go to Dashboard
            - **Ctrl+W**: Go to Workflow Manager
            - **Ctrl+L**: Go to System Monitor (Logs)
            - **Ctrl+,**: Open Settings
            - **F1**: Open Help
            
            ### Workflow Actions
            - **Space**: Start/Pause current operation
            - **Esc**: Cancel current operation
            - **Ctrl+S**: Save current state
            - **Ctrl+R**: Retry failed operation
            
            ### Interface
            - **Ctrl+B**: Toggle sidebar
            - **Ctrl++**: Zoom in
            - **Ctrl+-**: Zoom out
            - **Ctrl+0**: Reset zoom
            
            Note: Keyboard shortcuts can be customized in the Settings page.
            """
        },
        "api_configuration": {
            "title": "API Configuration",
            "content": """
            ## Setting Up APIs
            
            ### OpenAI API
            1. Get your API key from OpenAI
            2. Set the OPENAI_API_KEY environment variable
            3. Or configure it in the application settings
            4. Test the connection using the TTS page
            
            ### Cost Management
            - Monitor API usage in the Dashboard
            - Set usage limits to control costs
            - Use cost estimation before processing
            
            ### Rate Limiting
            - The system automatically handles rate limits
            - Adjust retry settings if needed
            - Monitor API response times
            """
        }
    }

def get_onboarding_steps() -> List[Dict]:
    """Get onboarding tutorial steps"""
    return [
        {
            "title": "Welcome to Dreamlet!",
            "content": "Let's take a quick tour of the video production system.",
            "action": "next"
        },
        {
            "title": "Dashboard Overview",
            "content": "The Dashboard shows all your projects and their status. You can monitor progress and start workflows from here.",
            "page": "00_Dashboard",
            "action": "visit"
        },
        {
            "title": "Workflow Manager",
            "content": "Use the Workflow Manager to create templates and automate your video production pipeline.",
            "page": "11_Workflow_Manager",
            "action": "visit"
        },
        {
            "title": "Processing Pages",
            "content": "Pages 01-10 handle different steps of video production. You can run them individually or as part of a workflow.",
            "action": "next"
        },
        {
            "title": "System Monitor",
            "content": "Monitor system health, view logs, and track performance metrics here.",
            "page": "12_System_Monitor",
            "action": "visit"
        },
        {
            "title": "Settings & Help",
            "content": "Customize your experience and access help documentation in the Settings page.",
            "page": "13_User_Settings",
            "action": "visit"
        },
        {
            "title": "You're Ready!",
            "content": "You've completed the tour. Start by adding your content to the input directory and visit the Dashboard.",
            "action": "finish"
        }
    ]

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    """Render page header"""
    st.title("⚙️ User Settings")
    st.markdown("*Customize your Dreamlet experience, configure notifications, and access help*")

def render_general_settings(settings: Dict):
    """Render general application settings"""
    st.subheader("🎛️ General Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Appearance**")
        settings["general"]["theme"] = st.selectbox(
            "Theme",
            ["light", "dark", "auto"],
            index=["light", "dark", "auto"].index(settings["general"]["theme"]),
            key="theme_select"
        )
        
        settings["general"]["compact_mode"] = st.checkbox(
            "Compact Mode",
            value=settings["general"]["compact_mode"],
            help="Reduce spacing and use smaller UI elements"
        )
        
        settings["general"]["show_tooltips"] = st.checkbox(
            "Show Tooltips",
            value=settings["general"]["show_tooltips"],
            help="Display helpful tooltips throughout the interface"
        )
        
        st.write("**Language & Localization**")
        settings["general"]["language"] = st.selectbox(
            "Language",
            ["en", "es", "fr", "de", "zh"],
            index=["en", "es", "fr", "de", "zh"].index(settings["general"]["language"]),
            format_func=lambda x: {"en": "English", "es": "Español", "fr": "Français", "de": "Deutsch", "zh": "中文"}[x]
        )
    
    with col2:
        st.write("**Auto-Refresh**")
        settings["general"]["auto_refresh"] = st.checkbox(
            "Enable Auto-Refresh",
            value=settings["general"]["auto_refresh"],
            help="Automatically refresh data on certain pages"
        )
        
        if settings["general"]["auto_refresh"]:
            settings["general"]["auto_refresh_interval"] = st.slider(
                "Refresh Interval (seconds)",
                min_value=10,
                max_value=300,
                value=settings["general"]["auto_refresh_interval"],
                step=10
            )
        
        st.write("**UI Preferences**")
        settings["ui"]["sidebar_collapsed"] = st.checkbox(
            "Collapse Sidebar by Default",
            value=settings["ui"]["sidebar_collapsed"]
        )
        
        settings["ui"]["show_system_metrics"] = st.checkbox(
            "Show System Metrics",
            value=settings["ui"]["show_system_metrics"],
            help="Display system resource usage in the interface"
        )
        
        settings["ui"]["table_page_size"] = st.slider(
            "Table Page Size",
            min_value=10,
            max_value=100,
            value=settings["ui"]["table_page_size"],
            step=5,
            help="Number of rows to display in tables"
        )

def render_notification_settings(settings: Dict):
    """Render notification configuration"""
    st.subheader("🔔 Notification Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**General Notifications**")
        settings["notifications"]["enabled"] = st.checkbox(
            "Enable Notifications",
            value=settings["notifications"]["enabled"]
        )
        
        if settings["notifications"]["enabled"]:
            settings["notifications"]["browser_notifications"] = st.checkbox(
                "Browser Notifications",
                value=settings["notifications"]["browser_notifications"],
                help="Show notifications in your browser"
            )
            
            settings["notifications"]["sound_enabled"] = st.checkbox(
                "Sound Notifications",
                value=settings["notifications"]["sound_enabled"],
                help="Play sound for notifications"
            )
        
        st.write("**Email Notifications**")
        settings["notifications"]["email_notifications"] = st.checkbox(
            "Enable Email Notifications",
            value=settings["notifications"]["email_notifications"]
        )
        
        if settings["notifications"]["email_notifications"]:
            settings["notifications"]["email_address"] = st.text_input(
                "Email Address",
                value=settings["notifications"]["email_address"],
                help="Email address for notifications"
            )
    
    with col2:
        st.write("**Notification Types**")
        
        if settings["notifications"]["enabled"]:
            settings["notifications"]["notify_on_completion"] = st.checkbox(
                "Workflow Completion",
                value=settings["notifications"]["notify_on_completion"],
                help="Notify when workflows complete successfully"
            )
            
            settings["notifications"]["notify_on_errors"] = st.checkbox(
                "Errors",
                value=settings["notifications"]["notify_on_errors"],
                help="Notify when errors occur"
            )
            
            settings["notifications"]["notify_on_warnings"] = st.checkbox(
                "Warnings",
                value=settings["notifications"]["notify_on_warnings"],
                help="Notify for warning messages"
            )
        
        st.write("**Test Notifications**")
        if st.button("Test Browser Notification"):
            st.success("🔔 Test notification sent!")
            # In a real implementation, this would trigger a browser notification
        
        if st.button("Test Email Notification") and settings["notifications"]["email_address"]:
            st.success(f"📧 Test email sent to {settings['notifications']['email_address']}")
            # In a real implementation, this would send an actual email

def render_workflow_settings(settings: Dict):
    """Render workflow configuration"""
    st.subheader("⚙️ Workflow Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Checkpoint Management**")
        settings["workflow"]["auto_save_checkpoints"] = st.checkbox(
            "Auto-Save Checkpoints",
            value=settings["workflow"]["auto_save_checkpoints"],
            help="Automatically save progress checkpoints during workflows"
        )
        
        if settings["workflow"]["auto_save_checkpoints"]:
            settings["workflow"]["checkpoint_interval"] = st.slider(
                "Checkpoint Interval (seconds)",
                min_value=60,
                max_value=1800,
                value=settings["workflow"]["checkpoint_interval"],
                step=60,
                help="How often to save checkpoints"
            )
        
        st.write("**Error Handling**")
        settings["workflow"]["auto_retry_failed_steps"] = st.checkbox(
            "Auto-Retry Failed Steps",
            value=settings["workflow"]["auto_retry_failed_steps"],
            help="Automatically retry failed workflow steps"
        )
        
        if settings["workflow"]["auto_retry_failed_steps"]:
            settings["workflow"]["max_retry_attempts"] = st.slider(
                "Max Retry Attempts",
                min_value=1,
                max_value=10,
                value=settings["workflow"]["max_retry_attempts"],
                help="Maximum number of retry attempts"
            )
    
    with col2:
        st.write("**Workflow Behavior**")
        settings["workflow"]["pause_on_errors"] = st.checkbox(
            "Pause on Errors",
            value=settings["workflow"]["pause_on_errors"],
            help="Pause workflow execution when errors occur"
        )
        
        settings["workflow"]["show_progress_details"] = st.checkbox(
            "Show Progress Details",
            value=settings["workflow"]["show_progress_details"],
            help="Display detailed progress information during execution"
        )
        
        st.write("**Performance Settings**")
        settings["performance"]["max_concurrent_processes"] = st.slider(
            "Max Concurrent Processes",
            min_value=1,
            max_value=8,
            value=settings["performance"]["max_concurrent_processes"],
            help="Maximum number of processes to run simultaneously"
        )
        
        settings["performance"]["memory_limit_mb"] = st.slider(
            "Memory Limit (MB)",
            min_value=1024,
            max_value=16384,
            value=settings["performance"]["memory_limit_mb"],
            step=512,
            help="Maximum memory usage for processing"
        )

def render_keyboard_shortcuts(settings: Dict):
    """Render keyboard shortcuts configuration"""
    st.subheader("⌨️ Keyboard Shortcuts")
    
    st.info("Customize keyboard shortcuts for quick access to features")
    
    shortcuts = settings["keyboard_shortcuts"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Navigation Shortcuts**")
        shortcuts["refresh"] = st.text_input("Refresh", value=shortcuts["refresh"])
        shortcuts["dashboard"] = st.text_input("Dashboard", value=shortcuts["dashboard"])
        shortcuts["workflow"] = st.text_input("Workflow Manager", value=shortcuts["workflow"])
        shortcuts["logs"] = st.text_input("System Monitor", value=shortcuts["logs"])
    
    with col2:
        st.write("**Application Shortcuts**")
        shortcuts["settings"] = st.text_input("Settings", value=shortcuts["settings"])
        shortcuts["help"] = st.text_input("Help", value=shortcuts["help"])
        
        st.write("**Actions**")
        if st.button("Reset to Defaults"):
            default_shortcuts = get_default_settings()["keyboard_shortcuts"]
            settings["keyboard_shortcuts"] = default_shortcuts
            st.success("Keyboard shortcuts reset to defaults")
            st.rerun()

def render_help_system():
    """Render help and documentation system"""
    st.subheader("❓ Help & Documentation")
    
    help_content = get_help_content()
    
    # Help topics selection
    help_topics = list(help_content.keys())
    topic_names = [help_content[topic]["title"] for topic in help_topics]
    
    selected_topic_idx = st.selectbox(
        "Select Help Topic",
        range(len(topic_names)),
        format_func=lambda x: topic_names[x],
        key="help_topic_select"
    )
    
    selected_topic = help_topics[selected_topic_idx]
    topic_data = help_content[selected_topic]
    
    # Display help content
    st.markdown(f"## {topic_data['title']}")
    st.markdown(topic_data['content'])
    
    # Quick actions
    st.write("**Quick Actions**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📖 Start Tutorial"):
            st.session_state.start_onboarding = True
            st.success("Tutorial started! Follow the guided tour.")
    
    with col2:
        if st.button("🎥 Video Tutorials"):
            st.info("Video tutorials would open here")
    
    with col3:
        if st.button("💬 Get Support"):
            st.info("Support contact information would be displayed here")

def render_onboarding_system(settings: Dict):
    """Render onboarding tutorial system"""
    st.subheader("🎓 Onboarding & Tutorial")
    
    onboarding_settings = settings["onboarding"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Tutorial Status**")
        if onboarding_settings["completed"]:
            st.success("✅ Onboarding completed")
        else:
            st.info(f"📍 Step {onboarding_settings['current_step'] + 1} of {len(get_onboarding_steps())}")
        
        st.write("**Tutorial Preferences**")
        onboarding_settings["skip_intro"] = st.checkbox(
            "Skip Introduction",
            value=onboarding_settings["skip_intro"],
            help="Skip the introduction step in tutorials"
        )
        
        onboarding_settings["show_tips"] = st.checkbox(
            "Show Tips",
            value=onboarding_settings["show_tips"],
            help="Display helpful tips throughout the interface"
        )
    
    with col2:
        st.write("**Tutorial Actions**")
        
        if st.button("🔄 Restart Tutorial"):
            onboarding_settings["completed"] = False
            onboarding_settings["current_step"] = 0
            st.success("Tutorial reset! Visit the Dashboard to start.")
        
        if st.button("✅ Mark as Completed"):
            onboarding_settings["completed"] = True
            onboarding_settings["current_step"] = len(get_onboarding_steps())
            st.success("Tutorial marked as completed!")
        
        if not onboarding_settings["completed"]:
            if st.button("▶️ Continue Tutorial"):
                st.info("Continue the tutorial from where you left off")

def render_import_export(settings: Dict):
    """Render settings import/export functionality"""
    st.subheader("📁 Import/Export Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Export Settings**")
        st.write("Save your current settings to a file for backup or sharing.")
        
        if st.button("📤 Export Settings"):
            settings_json = export_settings(settings)
            
            st.download_button(
                label="💾 Download Settings File",
                data=settings_json,
                file_name=f"dreamlet_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with col2:
        st.write("**Import Settings**")
        st.write("Load settings from a previously exported file.")
        
        uploaded_file = st.file_uploader("Choose settings file", type="json")
        
        if uploaded_file is not None:
            try:
                settings_content = uploaded_file.read().decode('utf-8')
                success, message, imported_settings = import_settings(settings_content)
                
                if success:
                    st.success(message)
                    if st.button("✅ Apply Imported Settings"):
                        # Update settings with imported values
                        settings.update(imported_settings)
                        save_user_settings(settings)
                        st.success("Settings imported and applied successfully!")
                        st.rerun()
                else:
                    st.error(message)
                    
            except Exception as e:
                st.error(f"Failed to read settings file: {e}")

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application function"""
    render_header()
    
    # Load current settings
    if "user_settings" not in st.session_state:
        st.session_state.user_settings = load_user_settings()
    
    settings = st.session_state.user_settings
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "General", "Notifications", "Workflow", "Shortcuts", "Help", "Import/Export"
    ])
    
    with tab1:
        render_general_settings(settings)
        render_onboarding_system(settings)
    
    with tab2:
        render_notification_settings(settings)
    
    with tab3:
        render_workflow_settings(settings)
    
    with tab4:
        render_keyboard_shortcuts(settings)
    
    with tab5:
        render_help_system()
    
    with tab6:
        render_import_export(settings)
    
    # Save settings button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("💾 Save Settings", type="primary"):
            save_user_settings(settings)
            st.session_state.user_settings = settings
            st.success("Settings saved successfully!")
    
    with col2:
        if st.button("🔄 Reset to Defaults"):
            if st.button("⚠️ Confirm Reset", key="confirm_reset"):
                st.session_state.user_settings = get_default_settings()
                save_user_settings(st.session_state.user_settings)
                st.success("Settings reset to defaults!")
                st.rerun()
    
    with col3:
        if st.button("❌ Discard Changes"):
            st.session_state.user_settings = load_user_settings()
            st.info("Changes discarded")
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown(f"*User Settings v1.0.0 | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

if __name__ == "__main__":
    main()