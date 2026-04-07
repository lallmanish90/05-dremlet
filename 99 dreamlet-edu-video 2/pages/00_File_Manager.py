import streamlit as st
import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import List, Dict
from utils.file_operations import get_input_directory, get_output_directory, ensure_directory_exists

st.set_page_config(page_title="File Manager - Dreamlet", page_icon="📁")

class FileManager:
    def __init__(self):
        self.input_dir = get_input_directory()
        self.output_dir = get_output_directory()
        ensure_directory_exists(self.input_dir)
        ensure_directory_exists(self.output_dir)
    
    def get_directory_structure(self, path: str) -> Dict:
        """Get directory structure as nested dict"""
        structure = {"name": os.path.basename(path), "type": "folder", "children": []}
        
        try:
            for item in sorted(os.listdir(path)):
                if item.startswith('.'):
                    continue
                    
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    structure["children"].append(self.get_directory_structure(item_path))
                else:
                    file_size = os.path.getsize(item_path)
                    structure["children"].append({
                        "name": item,
                        "type": "file",
                        "size": file_size,
                        "path": item_path
                    })
        except PermissionError:
            pass
            
        return structure
    
    def create_zip_from_directory(self, directory_path: str) -> str:
        """Create ZIP file from directory"""
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip.close()
        
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    archive_name = os.path.relpath(file_path, directory_path)
                    zipf.write(file_path, archive_name)
        
        return temp_zip.name
    
    def extract_uploaded_files(self, uploaded_files: List, target_dir: str) -> List[str]:
        """Extract uploaded files to target directory"""
        extracted_files = []
        
        for uploaded_file in uploaded_files:
            file_path = os.path.join(target_dir, uploaded_file.name)
            
            # Create subdirectory if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Handle ZIP files
            if uploaded_file.name.endswith('.zip'):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                    temp_file.write(uploaded_file.read())
                    temp_file.flush()
                    
                    # Extract ZIP contents
                    extract_dir = os.path.join(target_dir, os.path.splitext(uploaded_file.name)[0])
                    ensure_directory_exists(extract_dir)
                    
                    with zipfile.ZipFile(temp_file.name, 'r') as zipf:
                        zipf.extractall(extract_dir)
                        extracted_files.extend([os.path.join(extract_dir, name) for name in zipf.namelist()])
                    
                    os.unlink(temp_file.name)
            else:
                # Regular file
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.read())
                extracted_files.append(file_path)
        
        return extracted_files
    
    def format_file_size(self, size: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def display_directory_tree(self, structure: Dict, level: int = 0):
        """Display directory structure in Streamlit"""
        indent = "  " * level
        
        if structure["type"] == "folder":
            st.write(f"{indent}📁 **{structure['name']}/**")
            for child in structure["children"]:
                self.display_directory_tree(child, level + 1)
        else:
            file_size = self.format_file_size(structure["size"])
            st.write(f"{indent}📄 {structure['name']} ({file_size})")

def main():
    st.title("File Manager")
    st.write("Upload files to input directory and download results from output directory")
    
    file_manager = FileManager()
    
    # Create tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Files", "📥 Download Results", "📋 Browse Files", "🗑️ Cleanup"])
    
    with tab1:
        st.header("Upload Files to Input Directory")
        st.write("Upload your educational content files (transcripts, slides, presentations)")
        
        # File upload section
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            accept_multiple_files=True,
            type=['txt', 'md', 'pptx', 'pdf', 'zip'],
            help="Supported formats: TXT, MD, PPTX, PDF, ZIP"
        )
        
        if uploaded_files:
            st.write(f"Selected {len(uploaded_files)} files:")
            for file in uploaded_files:
                file_size = file_manager.format_file_size(len(file.read()))
                file.seek(0)  # Reset file pointer
                st.write(f"- {file.name} ({file_size})")
            
            # Upload directory selection
            upload_path = st.text_input(
                "Upload to subdirectory (optional)",
                placeholder="e.g., Course_01/Lecture_01",
                help="Leave empty to upload to root input directory"
            )
            
            if st.button("Upload Files", type="primary"):
                try:
                    # Determine target directory
                    target_dir = file_manager.input_dir
                    if upload_path.strip():
                        target_dir = os.path.join(file_manager.input_dir, upload_path.strip())
                    
                    ensure_directory_exists(target_dir)
                    
                    # Extract files
                    with st.spinner("Uploading files..."):
                        extracted_files = file_manager.extract_uploaded_files(uploaded_files, target_dir)
                    
                    st.success(f"✅ Successfully uploaded {len(extracted_files)} files!")
                    
                    # Show uploaded files
                    with st.expander("View uploaded files"):
                        for file_path in extracted_files:
                            rel_path = os.path.relpath(file_path, file_manager.input_dir)
                            st.write(f"📄 {rel_path}")
                            
                except Exception as e:
                    st.error(f"❌ Upload failed: {str(e)}")
    
    with tab2:
        st.header("Download Results from Output Directory")
        st.write("Download processed videos and other output files")
        
        # Check if output directory has content
        try:
            output_structure = file_manager.get_directory_structure(file_manager.output_dir)
            has_content = len(output_structure["children"]) > 0
            
            if has_content:
                # Option to download specific files or entire output
                download_option = st.radio(
                    "Download option:",
                    ["Download entire output folder", "Browse and select specific files"]
                )
                
                if download_option == "Download entire output folder":
                    if st.button("Create Download Package", type="primary"):
                        try:
                            with st.spinner("Creating download package..."):
                                zip_path = file_manager.create_zip_from_directory(file_manager.output_dir)
                            
                            # Provide download button
                            with open(zip_path, 'rb') as zip_file:
                                st.download_button(
                                    label="📦 Download Output.zip",
                                    data=zip_file.read(),
                                    file_name="dreamlet_output.zip",
                                    mime="application/zip"
                                )
                            
                            # Cleanup temp file
                            os.unlink(zip_path)
                            
                        except Exception as e:
                            st.error(f"❌ Failed to create download package: {str(e)}")
                
                else:  # Browse and select specific files
                    st.write("**Output Directory Contents:**")
                    file_manager.display_directory_tree(output_structure)
                    
                    # File selection (simplified - in a real implementation, you'd want a more sophisticated file picker)
                    st.info("Use the 'Browse Files' tab for detailed file exploration and individual downloads")
                    
            else:
                st.info("📭 Output directory is empty. Process some files first!")
                
        except Exception as e:
            st.error(f"❌ Error accessing output directory: {str(e)}")
    
    with tab3:
        st.header("Browse Files")
        st.write("Explore input and output directories")
        
        # Directory selection
        browse_dir = st.selectbox(
            "Select directory to browse:",
            ["Input Directory", "Output Directory"]
        )
        
        target_dir = file_manager.input_dir if browse_dir == "Input Directory" else file_manager.output_dir
        
        try:
            structure = file_manager.get_directory_structure(target_dir)
            
            if len(structure["children"]) > 0:
                st.write(f"**{browse_dir} Contents:**")
                file_manager.display_directory_tree(structure)
                
                # Directory statistics
                total_files = 0
                total_size = 0
                
                def count_files(struct):
                    nonlocal total_files, total_size
                    if struct["type"] == "file":
                        total_files += 1
                        total_size += struct["size"]
                    elif struct["type"] == "folder":
                        for child in struct["children"]:
                            count_files(child)
                
                count_files(structure)
                
                st.info(f"📊 **Statistics:** {total_files} files, {file_manager.format_file_size(total_size)} total")
                
            else:
                st.info(f"📭 {browse_dir} is empty")
                
        except Exception as e:
            st.error(f"❌ Error browsing directory: {str(e)}")
    
    with tab4:
        st.header("Cleanup")
        st.write("Clean up input and output directories")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Clean Input Directory")
            if st.button("🗑️ Clear Input Directory", help="Remove all files from input directory"):
                if st.session_state.get('confirm_input_cleanup'):
                    try:
                        for item in os.listdir(file_manager.input_dir):
                            item_path = os.path.join(file_manager.input_dir, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                        st.success("✅ Input directory cleaned")
                        st.session_state.confirm_input_cleanup = False
                    except Exception as e:
                        st.error(f"❌ Cleanup failed: {str(e)}")
                else:
                    st.session_state.confirm_input_cleanup = True
                    st.warning("⚠️ Click again to confirm cleanup")
        
        with col2:
            st.subheader("Clean Output Directory")
            if st.button("🗑️ Clear Output Directory", help="Remove all files from output directory"):
                if st.session_state.get('confirm_output_cleanup'):
                    try:
                        for item in os.listdir(file_manager.output_dir):
                            item_path = os.path.join(file_manager.output_dir, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                        st.success("✅ Output directory cleaned")
                        st.session_state.confirm_output_cleanup = False
                    except Exception as e:
                        st.error(f"❌ Cleanup failed: {str(e)}")
                else:
                    st.session_state.confirm_output_cleanup = True
                    st.warning("⚠️ Click again to confirm cleanup")
    
    # Usage instructions
    with st.expander("📖 File Manager Usage Instructions"):
        st.markdown("""
        ### How to Use the File Manager
        
        #### 📤 Uploading Files
        1. **Select Files**: Choose your educational content files (transcripts, slides, presentations)
        2. **Organize**: Optionally specify a subdirectory path (e.g., `Course_01/Lecture_01`)
        3. **Upload**: Click "Upload Files" to transfer files to the input directory
        4. **ZIP Support**: Upload ZIP files for bulk content transfer
        
        #### 📥 Downloading Results
        1. **Full Download**: Get all processed files as a single ZIP package
        2. **Selective Download**: Browse and download specific files
        3. **Organized Output**: Files are organized by language and course structure
        
        #### 📋 File Browsing
        - **Directory View**: Explore input and output directory structures
        - **File Statistics**: See file counts and total storage usage
        - **Real-time Updates**: View changes as files are processed
        
        #### 🗑️ Cleanup Options
        - **Input Cleanup**: Remove source files after processing
        - **Output Cleanup**: Clear processed results to save space
        - **Confirmation Required**: Two-click confirmation prevents accidental deletion
        
        ### Supported File Types
        - **Text Files**: `.txt`, `.md` (transcripts and slide descriptions)
        - **Presentations**: `.pptx` (PowerPoint slides)
        - **Documents**: `.pdf` (document conversion)
        - **Archives**: `.zip` (bulk file upload)
        
        ### Tips for Best Results
        - Use descriptive folder names for organization
        - Upload related files together in ZIP archives
        - Regularly clean up directories to save storage space
        - Download results promptly after processing
        """)

if __name__ == "__main__":
    main()