# How to Modify Secrets in Remote .env (SOPS Encryption)

This guide shows how to securely modify secrets in the encrypted .env file on the Nebula server.

## 🔐 Methods to Modify Encrypted Secrets

### **Method 1: Interactive SOPS Editor (Recommended)**

```bash
# SSH to Nebula server
ssh nebula

# Edit encrypted .env with interactive editor
cd /opt/detektor
sops .env
```

**In the editor:**
- Add/modify any secret variables
- Save and exit - SOPS will automatically re-encrypt
- Example changes:
  ```bash
  RTSP_URL=rtsp://newuser:newpass@192.168.1.200:554/stream
  FRAME_BUFFER_SIZE=200
  ```

### **Method 2: Automated Script (One-liner)**

```bash
# Update RTSP URL via script
./scripts/deploy-rtsp-capture.sh configure-encrypted rtsp://admin:newpassword@192.168.1.100:554/stream
```

### **Method 3: Manual Command Line**

```bash
# SSH to Nebula
ssh nebula

# Update specific secret
cd /opt/detektor
echo 'RTSP_URL=rtsp://admin:newpassword@192.168.1.100:554/stream' > /tmp/new_rtsp
sops -e /tmp/new_rtsp > .env
rm /tmp/new_rtsp
```

### **Method 4: Batch Update Multiple Secrets**

```bash
# Create temporary file with all changes
ssh nebula << 'EOF'
cd /opt/detektor

# Create new configuration file
cat > /tmp/updates.env << 'EOL'
# RTSP Configuration
RTSP_URL=rtsp://newuser:newpassword@192.168.1.200:554/stream
RTSP_URL_MAIN=rtsp://admin:admin123@maincamera.local:554/stream
RTSP_URL_SUB=rtsp://user:userpass@subcamera.local:554/stream2

# Buffer Settings
FRAME_BUFFER_SIZE=150
RTSP_RECONNECT_TIMEOUT=10

# Camera Details
CAMERA_IP=192.168.1.200
CAMERA_USERNAME=newuser
CAMERA_PASSWORD=newpassword
CAMERA_PORT=554
EOL

# Encrypt and replace
sops -e /tmp/updates.env > .env
rm /tmp/updates.env
echo "✅ Secrets updated successfully"
EOF
```

## 📋 **Common Secret Updates**

### **Update RTSP Camera URL**
```bash
# Via SOPS editor
ssh nebula "cd /opt/detektor && sops .env"
# Change: RTSP_URL=rtsp://newuser:newpass@newip:554/stream

# Via one-liner
ssh nebula "cd /opt/detektor && echo 'RTSP_URL=rtsp://admin:newpass@192.168.1.150:554/stream' | sops -e > .env"
```

### **Update Camera Credentials**
```bash
# Update username/password
ssh nebula "cd /opt/detektor && sops .env"
# Change:
# CAMERA_USERNAME=newuser
# CAMERA_PASSWORD=newpass
# RTSP_URL=rtsp://newuser:newpass@192.168.1.100:554/stream
```

### **Update Buffer Size**
```bash
# Quick buffer size update
ssh nebula "cd /opt/detektor && sed 's/FRAME_BUFFER_SIZE=.*/FRAME_BUFFER_SIZE=200/' <<< 'FRAME_BUFFER_SIZE=200' | sops -e > .env"
```

## 🔄 **Verification After Changes**

```bash
# Verify changes
ssh nebula "cd /opt/detektor && sops -d .env | grep -E 'RTSP_URL|FRAME_BUFFER|CAMERA_'"

# Test RTSP connection
ssh nebula "cd /opt/detektor && docker exec rtsp-capture ffprobe \$(sops -d .env | grep '^RTSP_URL=' | cut -d'=' -f2-)"

# Restart service
./scripts/deploy-rtsp-capture.sh restart
```

## 📝 **Best Practices**

1. **Always use SOPS** for secret management
2. **Backup before changes**: `cp .env .env.backup.$(date +%Y%m%d_%H%M%S)`
3. **Test changes** before production deployment
4. **Use descriptive commit messages** in SOPS
5. **Verify decryption** after changes

## 🚨 **Important Notes**

- **Never commit plain text secrets** to git
- **SOPS automatically handles encryption** after editing
- **All changes are immediately encrypted** upon saving
- **Service restart required** after configuration changes

## 🎯 **Quick Reference**

| **Action** | **Command** |
|------------|-------------|
| **Edit interactively** | `ssh nebula "cd /opt/detektor && sops .env"` |
| **Update RTSP URL** | `./scripts/deploy-rtsp-capture.sh configure-encrypted rtsp://user:pass@ip:554/stream` |
| **View current** | `ssh nebula "cd /opt/detektor && sops -d .env | grep RTSP_URL"` |
| **Restart service** | `./scripts/deploy-rtsp-capture.sh restart` |
