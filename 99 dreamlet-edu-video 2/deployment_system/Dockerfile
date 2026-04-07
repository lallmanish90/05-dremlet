# Multi-stage Dockerfile for Dreamlet Educational Video Production System
# Stage 1: Build environment
FROM python:3.11-slim as builder

# Set build arguments for license key embedding
ARG LICENSE_KEY=""
ARG USER_ID=""
ARG LICENSE_SERVER_URL="https://license.dreamlet.com/api/validate"

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libhdf5-dev \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements and install Python dependencies
COPY ../pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy source code from parent directory
COPY ../ .
# Copy license validator from current directory
COPY license_validator.py .

# Compile Python files to bytecode and remove source
RUN python -m compileall -b . && \
    find . -name "*.py" -not -path "./license_validator.py" -delete && \
    find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Create license configuration file
RUN echo "LICENSE_KEY=${LICENSE_KEY}" > /build/.license_config && \
    echo "USER_ID=${USER_ID}" >> /build/.license_config && \
    echo "LICENSE_SERVER_URL=${LICENSE_SERVER_URL}" >> /build/.license_config

# Stage 2: Runtime environment
FROM python:3.11-slim as runtime

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    streamlit==1.44.1 \
    opencv-python-headless==4.11.0.86 \
    pillow==11.1.0 \
    numpy==2.2.4 \
    ffmpeg-python==0.2.0 \
    python-pptx==1.0.2 \
    python-docx==1.1.2 \
    pdf2image==1.17.0 \
    openai==1.72.0 \
    anthropic==0.50.0 \
    requests==2.32.3 \
    pandas==2.2.3 \
    psutil==7.0.0 \
    setuptools==78.1.0

# Create application user for security
RUN useradd -m -u 1001 dreamletuser && \
    mkdir -p /app /app/input /app/output && \
    chown -R dreamletuser:dreamletuser /app

# Switch to application user
USER dreamletuser

# Set working directory
WORKDIR /app

# Copy compiled bytecode from builder stage
COPY --from=builder --chown=dreamletuser:dreamletuser /build/*.pyc ./
COPY --from=builder --chown=dreamletuser:dreamletuser /build/pages/ ./pages/
COPY --from=builder --chown=dreamletuser:dreamletuser /build/utils/ ./utils/
COPY --from=builder --chown=dreamletuser:dreamletuser /build/config/ ./config/
COPY --from=builder --chown=dreamletuser:dreamletuser /build/.license_config ./.license_config

# Copy the license validator (kept as source for debugging if needed)
COPY --chown=dreamletuser:dreamletuser license_validator.py ./

# Create input and output directories with proper permissions
RUN mkdir -p input output

# Set environment variables
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false
ENV STREAMLIT_SERVER_FILE_WATCHER_TYPE=none

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Expose Streamlit port
EXPOSE 8501

# Create startup script that validates license before running app
RUN echo '#!/bin/bash\n\
python license_validator.py\n\
if [ $? -eq 0 ]; then\n\
    streamlit run app.pyc --server.port=8501 --server.address=0.0.0.0\n\
else\n\
    echo "License validation failed. Access denied."\n\
    exit 1\n\
fi' > /app/start.sh && chmod +x /app/start.sh

# Set the entrypoint
CMD ["/app/start.sh"]