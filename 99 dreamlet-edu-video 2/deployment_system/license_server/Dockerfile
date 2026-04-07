# License Server Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Create directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV FLASK_APP=app.py
ENV DATABASE_URL=sqlite:///data/licenses.db

# Expose port
EXPOSE 5000

# Create a non-root user
RUN useradd -m -u 1001 licenseuser && \
    chown -R licenseuser:licenseuser /app
USER licenseuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Run the application
CMD ["python", "app.py"]