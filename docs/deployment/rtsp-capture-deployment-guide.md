# RTSP Capture Service - Deployment Guide (Blok 5)

This guide covers the complete deployment process for the RTSP capture service on the Nebula server as specified in Blok 5 of the RTSP capture service documentation.

## Prerequisites

Before starting the deployment, ensure:
1. All previous blocks (0-4) are completed
2. Docker images are built and pushed to GitHub Container Registry
3. SSH access to Nebula server is configured
4. SOPS is installed for encrypted secrets management

## Security Configuration

### 🔐 Secrets Management with SOPS
The project uses **SOPS (Secrets Operations) with age encryption** for secure configuration management.

**Key points:**
- `.env` file is encrypted using SOPS
- RTSP credentials are stored encrypted
- No plain text passwords in configuration
- Uses age encryption keys

### SOPS Setup on Nebula Server

#### AGE Key Configuration
The project uses **AGE-SECRET-KEY-17Y3RLEZT98PR6J7M0X0TQC4SL7KYM4C6J7S5YDAHQ02YZM3NANNQZDTLDH** as the decryption key.

#### 1. Setup SOPS and AGE Key
```bash
# SSH to Nebula server
ssh nebula

# Install SOPS and age
sudo apt-get update && sudo apt-get install -y sops age

# Setup AGE key for SOPS
mkdir -p ~/.config/sops/age
cat > ~/.config/sops/age/keys.txt << 'EOF'
AGE-SECRET-KEY-17Y3RLEZT98PR6J7M0X0TQC4SL7KYM4C6J7S5YDAHQ02YZM3NANNQZDTLDH
EOF
chmod 600 ~/.config/sops/age/keys.txt

# Alternative: Use environment variable
echo 'export SOPS_AGE_KEY="AGE-SECRET-KEY-17Y3RLEZT98PR6J7M0X0TQC4SL7KYM4C6J7S5YDAHQ02YZM3NANNQZDTLDH"' >> ~/.bashrc
source ~/.bashrc
```

#### 2. Copy .sops.yaml to server
```bash
# Copy .sops.yaml to Nebula
scp .sops.yaml nebula:/opt/detektor/
```

#### 3. Verify SOPS Setup
```bash
# Test decryption
ssh nebula "cd /opt/detektor && SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt sops -d .env"

# Or with environment variable
ssh nebula "cd /opt/detektor && SOPS_AGE_KEY=AGE-SECRET-KEY-17Y3RLEZT98PR6J7M0X0TQC4SL7KYM4C6J7S5YDAHQ02YZM3NANNQZDTLDH sops -d .env"
```

## Deployment Steps

### 1. Configure RTSP Stream via Encrypted .env

Use SOPS to securely configure the RTSP URL:

```bash
# Method 1: Use the deployment script (recommended)
./scripts/deploy-rtsp-capture.sh configure-encrypted rtsp://username:password@camera_ip:554/stream

# Method 2: Manual SOPS configuration
ssh nebula
cd /opt/detektor
sops .env
```

**Add these variables to the encrypted .env:**
```bash
RTSP_URL=rtsp://admin:password@192.168.1.100:554/stream
FRAME_BUFFER_SIZE=100
```

### 2. Deploy via Deployment Script

The RTSP capture service has been integrated into the main deployment script. To deploy:

```bash
# Deploy all services including RTSP capture
./scripts/deploy-to-nebula.sh

# Or deploy RTSP capture service using encrypted .env
./scripts/deploy-rtsp-capture.sh full
```

### 3. Verify RTSP Connection

Check the RTSP connection using the encrypted configuration:

```bash
# Check current RTSP URL from encrypted .env
ssh nebula "cd /opt/detektor && SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key sops -d .env | grep RTSP_URL"

# Test RTSP connection
ssh nebula "docker exec rtsp-capture ffprobe -v quiet -print_format json -show_streams \$(SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key sops -d .env | grep '^RTSP_URL=' | cut -d'=' -f2-)"

# Check service logs
ssh nebula "docker logs rtsp-capture -f"
```

### 4. Verification of Metrics in Prometheus

Access Prometheus at `http://nebula:9090` and verify the following metrics:

```promql
# Frame capture rate
rate(rtsp_frames_captured_total[5m])

# Processing latency
histogram_quantile(0.99, rtsp_frame_processing_duration_seconds)

# Connection status
rtsp_connection_status{camera_id="main"}

# Error rate
rate(rtsp_errors_total[5m])

# Buffer size
rtsp_buffer_size
```

### 5. Integration with Jaeger Tracing

Verify traces are available in Jaeger:

1. Access Jaeger UI at `http://nebula:16686`
2. Select service: `rtsp-capture`
3. Look for traces with operations:
   - `frame.capture`
   - `frame.buffer`
   - `frame.queue`

Check traces via API:
```bash
curl http://nebula:16686/api/traces?service=rtsp-capture
```

### 6. Load Testing

Run a comprehensive load test to ensure stability:

```bash
# Run 5-minute load test
./scripts/deploy-rtsp-capture.sh load-test

# Manual monitoring
ssh nebula "watch -n 5 'curl -s localhost:8001/metrics | grep rtsp_'"
```

#### Expected Metrics During Load Test:
- CPU usage: <50%
- Memory usage: <500MB
- 0% frame loss
- Stable connection for 24+ hours

## SOPS Configuration Management

### Adding RTSP URL to Encrypted .env

```bash
# SSH to Nebula
ssh nebula
cd /opt/detektor

# Edit encrypted configuration
sops .env

# Add these lines:
RTSP_URL=rtsp://admin:password@192.168.1.100:554/stream
FRAME_BUFFER_SIZE=100
```

### Viewing Current Configuration

```bash
# View decrypted configuration
ssh nebula "cd /opt/detektor && SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key sops -d .env"

# Check specific variables
ssh nebula "cd /opt/detektor && SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key sops -d .env | grep RTSP_URL"
```

### Security Best Practices

1. **Never commit plain text secrets**
2. **Use SOPS for all sensitive configuration**
3. **Rotate encryption keys regularly**
4. **Verify .sops.yaml has correct public keys**
5. **Test decryption on target server before deployment**

## Troubleshooting

### Common Issues and Solutions

#### RTSP Connection Failed
```bash
# Check encrypted configuration
ssh nebula "cd /opt/detektor && SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key sops -d .env | grep RTSP_URL"

# Test camera accessibility
ssh nebula "docker exec rtsp-capture ffprobe \$(SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key sops -d .env | grep '^RTSP_URL=' | cut -d'=' -f2-)"

# Check network connectivity
ssh nebula "docker exec rtsp-capture ping camera_ip"
```

#### SOPS Decryption Issues
```bash
# Verify SOPS installation
ssh nebula "which sops && sops --version"

# Check encryption key
ssh nebula "ls -la /opt/detektor/.sops-key"

# Test decryption manually
ssh nebula "cd /opt/detektor && SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key sops -d .env"
```

#### No Metrics in Prometheus
```bash
# Check service health
curl http://nebula:8001/health

# Verify metrics endpoint
curl http://nebula:8001/metrics

# Check Prometheus configuration
curl http://nebula:9090/api/v1/targets
```

### Service Logs Analysis

Check service logs for errors:
```bash
# Recent logs
ssh nebula "docker logs rtsp-capture --tail 100 -f"

# Logs with errors
ssh nebula "docker logs rtsp-capture | grep -i error"

# Performance logs
ssh nebula "docker logs rtsp-capture | grep -E '(processing|latency|buffer)'"
```

### Restart and Recovery

If service needs restart:
```bash
# Safe restart with latest image
./scripts/deploy-rtsp-capture.sh restart

# Full redeployment
./scripts/deploy-to-nebula.sh
```

## Monitoring Dashboard

A Grafana dashboard for RTSP capture service is available at:
- URL: `http://nebula:3000`
- Dashboard: `RTSP Capture Service`
- Data source: Prometheus

## Security Considerations

- **RTSP credentials are encrypted** using SOPS
- **Service runs as non-root user**
- **Network isolation via Docker networks**
- **Health checks monitor service availability**
- **No plain text secrets in any configuration**

## Performance Optimization

### Resource Limits
```yaml
# In docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 256M
```

### Environment Variables in Encrypted .env
```bash
# Core RTSP configuration
RTSP_URL=rtsp://admin:password@192.168.1.100:554/stream
FRAME_BUFFER_SIZE=100
LOG_LEVEL=INFO

# Redis configuration
REDIS_HOST=redis
REDIS_PORT=6379
```

## Success Criteria

The deployment is considered successful when:

1. ✅ Service starts without errors
2. ✅ RTSP connection is established with encrypted credentials
3. ✅ Frames are being captured and buffered
4. ✅ Metrics are exported to Prometheus
5. ✅ Traces are visible in Jaeger
6. ✅ Service passes 24-hour load test
7. ✅ Resource usage stays within limits
8. ✅ Automatic recovery after disconnect/reconnect
9. ✅ All secrets are encrypted using SOPS

## 🚀 Usage Instructions (SOPS-Based)

**Configure RTSP URL with encryption:**
```bash
# Method 1: Use deployment script with SOPS
./scripts/deploy-rtsp-capture.sh configure-encrypted rtsp://admin:password@192.168.1.100:554/stream

# Method 2: Manual SOPS configuration
ssh nebula
cd /opt/detektor
sops .env
# Add: RTSP_URL=rtsp://admin:password@192.168.1.100:554/stream
```

**Deploy using encrypted .env:**
```bash
# Full deployment with encrypted configuration
./scripts/deploy-rtsp-capture.sh full

# Or use main deployment script
./scripts/deploy-to-nebula.sh
```

**Verify encrypted configuration:**
```bash
# Check RTSP configuration
./scripts/deploy-rtsp-capture.sh verify

# View encrypted RTSP URL
ssh nebula "cd /opt/detektor && SOPS_AGE_KEY_FILE=/opt/detektor/.sops-key sops -d .env | grep RTSP_URL"
```

**Complete workflow:**
```bash
# 1. Configure encrypted RTSP URL
./scripts/deploy-rtsp-capture.sh configure-encrypted rtsp://user:pass@camera:554/stream

# 2. Deploy services
./scripts/deploy-to-nebula.sh

# 3. Verify deployment
./scripts/test-rtsp-deployment.sh
```

## Next Steps

After successful deployment:
1. Configure alerting rules for critical metrics
2. Set up log aggregation
3. Create performance baselines
4. Document camera-specific configurations
5. Plan scaling for additional cameras
6. Regular security audits of SOPS configuration
