# Dreamlet Educational Video Production System
## Docker Deployment Guide

### 🎯 Overview

This guide covers the complete deployment process for the Dockerized Dreamlet Educational Video Production System with license control. The system provides:

- **Source Code Protection**: Code compiled to bytecode and hidden in Docker containers
- **License Control**: Remote license validation with revocation capabilities
- **Cross-Platform Support**: Works on Windows, Mac, and Linux
- **Hybrid File Access**: Both local folder mounting and web-based file upload/download
- **No Installation Required**: Users only need Docker

---

## 🏗️ System Architecture

### Components

1. **Main Application Container**: Streamlit app with license validation
2. **License Server**: Flask API for license management (separate deployment)
3. **Setup Scripts**: Platform-specific deployment automation
4. **File Access**: Volume mounting + web-based file management

### Security Features

- **Bytecode Compilation**: Python source code compiled to `.pyc` files
- **License Validation**: Remote server validation with local caching
- **Hardware Fingerprinting**: Additional security layer
- **Time-based Fallback**: Embedded expiry dates as backup
- **User Tracking**: Comprehensive logging and validation tracking

---

## 🚀 Quick Start (Test User)

### 1. Start License Server

```bash
# Navigate to license server directory
cd license_server

# Start with Docker Compose
docker-compose up -d

# OR start manually
docker build -t dreamlet-license-server .
docker run -d -p 5000:5000 --name license-server dreamlet-license-server

# Note the Admin API Key from logs
docker logs license-server
```

### 2. Create Test License

```bash
# Add a test user (replace YOUR_ADMIN_API_KEY)
curl -X POST http://localhost:5000/api/admin/licenses \
  -H "X-API-Key: YOUR_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "email": "test@company.com",
    "company": "Test Company",
    "days_valid": 365
  }'
```

### 3. Build Test Docker Image

```bash
# Make build script executable (Unix)
chmod +x build_docker_image.sh

# Run interactive build
./build_docker_image.sh

# Follow prompts:
# - User ID: test_user
# - License Key: (use key from step 2)
# - License Server URL: http://host.docker.internal:5000/api/validate
# - Image Tag: dreamlet/educational-video-system:test_user
```

### 4. Test Deployment

```bash
# Navigate to generated deployment folder
cd deployments/test_user

# Windows: Double-click setup_windows.bat
# Mac/Linux: ./setup_unix.sh

# Access application at http://localhost:8501
```

---

## 📦 Production Deployment

### License Server Setup

1. **Deploy License Server**
   ```bash
   # Production deployment with persistent storage
   docker run -d \
     --name dreamlet-license-server \
     -p 5000:5000 \
     -v license_data:/app/data \
     -e SECRET_KEY="your_secure_secret_key" \
     -e ADMIN_API_KEY="your_secure_admin_key" \
     --restart unless-stopped \
     dreamlet-license-server:latest
   ```

2. **Configure SSL/Domain**
   - Set up reverse proxy (nginx/Apache)
   - Configure SSL certificate
   - Update LICENSE_SERVER_URL in build process

### User Management Workflow

1. **Create User License**
   ```bash
   curl -X POST https://your-license-server.com/api/admin/licenses \
     -H "X-API-Key: YOUR_ADMIN_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "employee_id",
       "email": "employee@company.com", 
       "company": "Your Company",
       "days_valid": 365
     }'
   ```

2. **Build User-Specific Image**
   ```bash
   ./build_docker_image.sh
   # Enter user details and license key from step 1
   ```

3. **Distribute to User**
   - Package the `deployments/user_id/` folder
   - Send to user with Docker installation instructions
   - User runs platform-specific setup script

4. **User Onboarding**
   - User installs Docker Desktop
   - User runs provided setup script
   - User accesses application via browser

### License Management

**List All Licenses:**
```bash
curl -X GET https://your-license-server.com/api/admin/licenses \
  -H "X-API-Key: YOUR_ADMIN_KEY"
```

**Revoke License:**
```bash
curl -X DELETE https://your-license-server.com/api/admin/licenses/employee_id \
  -H "X-API-Key: YOUR_ADMIN_KEY"
```

**Extend License:**
```bash
curl -X PUT https://your-license-server.com/api/admin/licenses/employee_id \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"days_extend": 90}'
```

**View Usage Statistics:**
```bash
curl -X GET https://your-license-server.com/api/admin/stats \
  -H "X-API-Key: YOUR_ADMIN_KEY"
```

---

## 🖥️ Platform-Specific Instructions

### Windows Deployment

**Prerequisites:**
- Docker Desktop for Windows
- Windows 10/11 or Windows Server 2019+

**User Instructions:**
1. Install Docker Desktop
2. Extract deployment package
3. Double-click `setup_windows.bat`
4. Wait for setup completion
5. Browser opens automatically to `http://localhost:8501`

### Mac Deployment

**Prerequisites:**
- Docker Desktop for Mac
- macOS 10.14+ (Intel) or macOS 11+ (Apple Silicon)

**User Instructions:**
1. Install Docker Desktop
2. Extract deployment package
3. Open Terminal, navigate to folder
4. Run `./setup_unix.sh`
5. Browser opens automatically to `http://localhost:8501`

### Linux Deployment

**Prerequisites:**
- Docker Engine or Docker Desktop
- Recent Linux distribution (Ubuntu 20.04+, CentOS 8+, etc.)

**User Instructions:**
1. Install Docker (varies by distribution)
2. Extract deployment package
3. Open terminal, navigate to folder
4. Run `./setup_unix.sh`
5. Open browser to `http://localhost:8501`

---

## 📂 File Management

### Method 1: Local Folders (Recommended)

After running setup script:
- **Input Folder**: `dreamlet_input/` - Put source files here
- **Output Folder**: `dreamlet_output/` - Results appear here

### Method 2: Web Interface

1. Open File Manager page in application
2. Upload files directly through browser
3. Download results as ZIP packages

### Folder Structure Example

```
dreamlet_input/
├── Course_01/
│   ├── Lecture_01/
│   │   ├── transcript.txt
│   │   ├── slides.txt
│   │   └── presentation.pptx
│   └── Lecture_02/
│       └── ...
└── Course_02/
    └── ...

dreamlet_output/
├── English/
│   ├── Course_01/
│   │   └── Lecture_01.mp4
│   └── Course_02/
└── Spanish/
    └── ...
```

---

## 🔧 Troubleshooting

### Common Issues

**License Validation Fails:**
1. Check internet connection
2. Verify license server is accessible
3. Check license hasn't expired
4. Ensure Docker container can reach license server

**Docker Won't Start:**
1. Ensure Docker Desktop is running
2. Check port 8501 is available
3. Verify volume permissions (Linux/Mac)
4. Check Docker logs: `docker logs dreamlet-app`

**File Access Issues:**
1. Verify folder permissions
2. Check volume mounting in Docker command
3. Try web-based file upload as alternative
4. Ensure input files are in correct format

### Debug Commands

```bash
# Check container status
docker ps

# View application logs
docker logs dreamlet-app

# Check license validation
docker exec dreamlet-app python license_validator.py

# Access container shell
docker exec -it dreamlet-app /bin/bash

# Test license server
curl http://localhost:5000/api/health
```

### License Server Debug

```bash
# Check license server logs
docker logs license-server

# Test validation endpoint
curl -X POST http://localhost:5000/api/validate \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "license_key": "TEST_KEY"}'

# View validation logs
curl -X GET http://localhost:5000/api/admin/logs?limit=10 \
  -H "X-API-Key: YOUR_ADMIN_KEY"
```

---

## 🔒 Security Considerations

### Source Code Protection

- All Python files compiled to bytecode (`.pyc`)
- Original source files removed from Docker image
- Multi-stage build excludes development tools
- License validator kept as source for debugging only

### License Security

- Unique license keys per user
- Hardware fingerprinting for additional validation
- Remote revocation capability
- Validation attempt logging
- Fallback time-based expiry

### Network Security

- Use HTTPS for license server
- Consider VPN for enterprise deployment
- Firewall rules for license server access
- Regular security updates for Docker images

### Data Security

- User data stays on local machine
- No cloud storage of sensitive content
- Volume mounts for secure file access
- Optional web upload with session cleanup

---

## 📊 Monitoring & Analytics

### License Server Metrics

Monitor through admin API:
- Active license count
- Validation attempts per user
- Failed validation reasons
- Usage patterns and trends

### Application Monitoring

- Docker container health checks
- Resource usage monitoring
- Application performance metrics
- User activity tracking

### Alerting

Set up alerts for:
- License server downtime
- High validation failure rates
- Expired licenses needing renewal
- Container failures or crashes

---

## 🚀 Scaling & Advanced Deployment

### Multi-Instance Deployment

```bash
# Load balancer with multiple license servers
docker run -d --name license-server-1 -p 5001:5000 dreamlet-license-server
docker run -d --name license-server-2 -p 5002:5000 dreamlet-license-server

# Use nginx for load balancing and SSL termination
```

### Enterprise Features

- **LDAP/AD Integration**: Sync user licenses with corporate directory
- **Audit Logging**: Comprehensive logging for compliance
- **Backup & Recovery**: Automated backup of license database
- **High Availability**: Clustered license server deployment

### Automated Deployment

Create CI/CD pipelines for:
- Automated image building per user
- License provisioning workflows
- Update deployment processes
- Monitoring and alerting setup

---

## 📋 Appendices

### A. Environment Variables

**License Server:**
- `SECRET_KEY`: Flask secret key
- `ADMIN_API_KEY`: Admin API access key
- `DATABASE_URL`: SQLite database path
- `PORT`: Server port (default: 5000)

**Application Container:**
- `LICENSE_KEY`: Embedded user license key
- `USER_ID`: Embedded user identifier
- `LICENSE_SERVER_URL`: License validation endpoint
- `FALLBACK_EXPIRY`: Backup expiry date

### B. API Reference

Complete API documentation for license server endpoints available at:
`http://your-license-server/api/docs` (if Swagger is enabled)

### C. File Format Support

**Input Formats:**
- Text: `.txt`, `.md`
- Presentations: `.pptx`
- Archives: `.zip`
- Documents: `.pdf`

**Output Formats:**
- Video: `.mp4` (4K resolution)
- Audio: `.mp3`, `.wav`
- Images: `.png` (4K resolution)

### D. Performance Guidelines

**System Requirements:**
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB free space per course
- **CPU**: 2 cores minimum, 4+ cores for video processing
- **Network**: Stable internet for license validation

**Optimization Tips:**
- Use SSD storage for better performance
- Allocate adequate RAM to Docker
- Enable hardware acceleration when available
- Process files in smaller batches for large courses