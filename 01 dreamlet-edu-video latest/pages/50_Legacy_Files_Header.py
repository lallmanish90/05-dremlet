"""
CODING CONVENTION: NO SHARED CODE
- All code for this page must be contained entirely within this single file
- Never import from other page files or create shared utilities
- Copy any needed functions directly into this file
- Each page is completely self-contained and independent
"""

import streamlit as st

st.set_page_config(page_title="Legacy Files", page_icon="📚")

st.title("Legacy Files")
st.markdown("""
---

The following pages contain legacy functionality that has been superseded by newer versions.
These are retained for backward compatibility and reference purposes.

---
""")

# Make the Legacy Files section collapsible and closed by default
# Also hide this header page from the sidebar
st.markdown(
    """
    <style>
    /* Hide this header page from the sidebar */
    [data-testid="stSidebarNav"] li:has(div:contains("Legacy Files Header")):not(:has(div:contains("Adjust Slide Files Only"))) {
        display: none;
    }
    
    /* Create a collapsible section for Legacy Files */
    [data-testid="stSidebarNav"] li:has(div:contains("Legacy Files")):not(:has(div:contains("Legacy Files Header"))) div {
        font-weight: bold;
        color: rgba(49, 51, 63, 0.6);
        margin-top: 20px;
        margin-bottom: 4px;
        border-bottom: 1px solid rgba(49, 51, 63, 0.2);
    }
    
    /* Style Legacy Files as a collapsible section header */
    [data-testid="stSidebarNav"] li:has(div:contains("Legacy Files")):not(:has(div:contains("Legacy Files Header"))) {
        cursor: pointer;
    }

    /* Hide all legacy items by default */
    [data-testid="stSidebarNav"] li:has(div:contains("Adjust Slide Files Only")),
    [data-testid="stSidebarNav"] li:has(div:contains("multilingual folder structure")),
    [data-testid="stSidebarNav"] li:has(div:contains("Convert Text to multiple languages")),
    [data-testid="stSidebarNav"] li:has(div:contains("Multilingual TTS")),
    [data-testid="stSidebarNav"] li:has(div:contains("TTS Open AI")),
    [data-testid="stSidebarNav"] li:has(div:contains("TTS Kokoro old")),
    [data-testid="stSidebarNav"] li:has(div:contains("TTS Kokoro GPU old")),
    [data-testid="stSidebarNav"] li:has(div:contains("Translator Lecto")),
    [data-testid="stSidebarNav"] li:has(div:contains("count old")),
    [data-testid="stSidebarNav"] li:has(div:contains("mp4 CPU")) {
        display: none;
    }
    </style>

    <script>
    // JavaScript to toggle the collapsible section
    const observer = new MutationObserver(() => {
        const legacyHeader = Array.from(document.querySelectorAll('[data-testid="stSidebarNav"] li')).find(
            el => el.textContent.includes('Legacy Files') && !el.textContent.includes('Legacy Files Header')
        );
        
        if (legacyHeader && !legacyHeader.onclick) {
            legacyHeader.onclick = () => {
                const legacyItems = Array.from(document.querySelectorAll('[data-testid="stSidebarNav"] li')).filter(
                    el => (
                        el.textContent.includes('Adjust Slide Files Only') ||
                        el.textContent.includes('multilingual folder structure') ||
                        el.textContent.includes('Convert Text to multiple languages') ||
                        el.textContent.includes('Multilingual TTS') ||
                        el.textContent.includes('TTS Open AI') ||
                        el.textContent.includes('TTS Kokoro old') ||
                        el.textContent.includes('TTS Kokoro GPU old') ||
                        el.textContent.includes('Translator Lecto') ||
                        el.textContent.includes('count old') ||
                        el.textContent.includes('mp4 CPU')
                    )
                );
                
                legacyItems.forEach(item => {
                    item.style.display = item.style.display === 'none' ? 'block' : 'none';
                });
            };
        }
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
    </script>
    """,
    unsafe_allow_html=True
)