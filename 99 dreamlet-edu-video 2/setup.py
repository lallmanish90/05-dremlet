import setuptools
import os
from pathlib import Path

# Read the requirements from pyproject.toml
dependencies = [
    "ffmpeg-python>=0.2.0",
    "numpy>=2.2.4",
    "openai>=1.72.0",
    "opencv-python>=4.11.0.86",
    "pillow>=11.1.0",
    "python-docx>=1.1.2",
    "python-pptx>=1.0.2",
    "streamlit>=1.44.1",
]

# Ensure directories exist
required_dirs = [
    "input",
    "output",
    ".streamlit",
]

for directory in required_dirs:
    os.makedirs(directory, exist_ok=True)

# Create .streamlit/config.toml if it doesn't exist
streamlit_config = Path(".streamlit/config.toml")
if not streamlit_config.exists():
    with open(streamlit_config, "w") as f:
        f.write("""[server]
headless = true
address = "0.0.0.0"
port = 5000
""")

setuptools.setup(
    name="dreamlet_video_production",
    version="0.1.0",
    author="",
    author_email="",
    description="Dreamlet Educational Video Production System",
    long_description="A Streamlit-powered educational video production automation tool",
    long_description_content_type="text/markdown",
    url="",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=dependencies,
    entry_points={
        "console_scripts": [
            "dreamlet=app:main",
        ],
    },
    include_package_data=True,
)