# 🚀 Deployment System

This folder contains all Docker deployment and license control files, keeping the main application root clean.

## 📁 Contents:

### **Docker & License System:**
- `Dockerfile` - Multi-stage secure Docker build
- `license_validator.py` - License validation system
- `license_server/` - Complete license management server

### **Build & Distribution:**
- `create_distribution.sh` - **SECURE** distribution creator (no source code)
- `build_docker_image.sh` - User-specific image builder
- `dreamlet_distribution/` - User-safe distribution folder

### **Legacy Scripts:**
- `setup_windows.bat` / `setup_unix.sh` - Simple setup scripts

### **Documentation:**
- Complete deployment guides and test results
- License management documentation
- Security implementation details

## 🎯 Usage:

### **Create Secure Distribution:**
```bash
cd deployment_system
./create_distribution.sh
```

### **Build User-Specific Image:**
```bash
cd deployment_system  
./build_docker_image.sh
```

This keeps all deployment complexity separate from your main educational video processing application.