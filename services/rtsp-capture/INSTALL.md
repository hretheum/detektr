# RTSP Capture Service - Installation Guide

## 🔧 System Requirements

- macOS 10.15+ / Ubuntu 20.04+
- Python 3.11+
- FFmpeg with RTSP support

## 📦 Installation Steps

### 1. Install FFmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Verify installation
ffmpeg -version
ffprobe -version
```

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
# Run environment check
python test_environment.py

# Should show all green checkmarks
```

## 🐛 Troubleshooting

### FFmpeg Issues

**Problem**: FFmpeg not found in PATH
```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Verify
which ffmpeg
which ffprobe
```

**Problem**: FFmpeg lacks RTSP support
```bash
# Check protocols
ffmpeg -protocols | grep rtsp

# Should show:
# rtsp (input/output protocol)
```

### PyAV Issues

**Problem**: PyAV compilation errors
```bash
# macOS - install system dependencies
brew install ffmpeg pkg-config

# Ubuntu - install development headers
sudo apt install libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev libavresample-dev

# Reinstall PyAV
pip uninstall av
pip install av
```

### OpenCV Issues

**Problem**: OpenCV import fails
```bash
# Try different OpenCV package
pip uninstall opencv-python
pip install opencv-python-headless

# Or install system OpenCV
# macOS: brew install opencv
# Ubuntu: sudo apt install python3-opencv
```

## 📋 Verification Checklist

After installation, verify:
- [ ] ✅ Python 3.11+ available
- [ ] ✅ FFmpeg installed and in PATH
- [ ] ✅ FFprobe installed and in PATH
- [ ] ✅ PyAV imports successfully
- [ ] ✅ OpenCV imports successfully
- [ ] ✅ All Python dependencies installed

## 🚀 Next Steps

Once environment is ready:

1. **Run tests**: `python -m pytest tests/test_rtsp_prerequisites.py -v`
2. **Start simulator**: `python rtsp_simulator.py`
3. **Test connection**: `python proof_of_concept.py`

## 📞 Support

If you encounter issues:
1. Check the error message carefully
2. Verify system dependencies are installed
3. Try in a fresh virtual environment
4. Check Python and FFmpeg versions
