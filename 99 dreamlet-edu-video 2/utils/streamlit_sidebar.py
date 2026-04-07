import streamlit as st

def organize_sidebar():
    """
    Organize the sidebar menu with a collapsible section for Legacy Files.
    This function should be called in the main app.py file.
    """
    # Add custom CSS to make the Legacy Files section collapsible and defaulting to closed
    st.markdown(
        """
        <style>
        .legacy-section {
            margin-top: 20px;
            margin-bottom: 20px;
        }
        .legacy-header {
            cursor: pointer;
            padding: 10px;
            background-color: #f0f2f6;
            border-radius: 5px;
            margin-bottom: 5px;
        }
        .legacy-content {
            display: none;
            padding-left: 15px;
        }
        </style>
        <script>
        // JavaScript to toggle the legacy content visibility
        document.addEventListener('DOMContentLoaded', function() {
            var legacyHeader = document.querySelector('.legacy-header');
            var legacyContent = document.querySelector('.legacy-content');
            
            legacyHeader.addEventListener('click', function() {
                if (legacyContent.style.display === 'none' || legacyContent.style.display === '') {
                    legacyContent.style.display = 'block';
                } else {
                    legacyContent.style.display = 'none';
                }
            });
        });
        </script>
        """,
        unsafe_allow_html=True
    )