# SOPS Editor Commands Guide

## How to Exit SOPS Interactive Editor

### Vim Editor (Default)
- **Save and Exit**: Press `ESC`, then type `:wq` and press `Enter`
- **Exit without saving**: Press `ESC`, then type `:q!` and press `Enter`
- **Force quit**: Press `ESC`, then type `:q!` and press `Enter`

### Nano Editor
- **Save and Exit**: Press `Ctrl+X`, then `Y`, then `Enter`
- **Exit without saving**: Press `Ctrl+X`, then `N`

## SOPS Command Reference

### Basic Commands
```bash
# View decrypted content
sops -d .env

# Edit encrypted file
sops .env

# Edit with specific editor
EDITOR=nano sops .env
EDITOR=code sops .env

# Extract specific key
sops -d --extract '["RTSP_URL_MAIN"]' .env

# Update specific key
sops --set '["RTSP_URL_MAIN"] "rtsp://new-url"' .env

# Add new key
sops --set '["NEW_KEY"] "new-value"' .env

# Rotate encryption keys
sops rotate -i .env
```

### Managing AGE Keys

#### List current recipients
```bash
sops -r .env
```

#### Add new recipient
```bash
sops -r -i --add-age age1newkey .env
```

#### Remove recipient
```bash
sops -r -i --rm-age age1oldkey .env
```

### Troubleshooting

#### Change default editor
```bash
export EDITOR=nano  # or vim, code, etc.
```

#### Check encryption status
```bash
grep -n '^[A-Z_][A-Z0-9_]*=' .env
```

### Common Patterns

#### View all RTSP related config
```bash
sops -d .env | grep -E '(RTSP|CAMERA)'
```

#### Update password only
```bash
sops --set '["CAMERA_PASSWORD"] "newsecurepassword"' .env
```

#### Batch update from file
```bash
sops --set '["CONFIG"] "'"$(cat config.json)"'"' .env
```

## Quick Reference Card

| Action | Command |
|--------|---------|
| **View** | `sops -d .env` |
| **Edit** | `sops .env` |
| **Save (Vim)** | `:wq` |
| **Quit (Vim)** | `:q!` |
| **Save (Nano)** | `Ctrl+X, Y, Enter` |
| **Quit (Nano)** | `Ctrl+X, N` |
| **Check keys** | `sops -r .env` |
| **Add key** | `sops -r -i --add-age age1... .env` |
