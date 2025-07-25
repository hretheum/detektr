# PgBouncer Service

## Overview
PgBouncer is a lightweight connection pooler for PostgreSQL that helps manage database connections efficiently.

## Configuration

### Authentication
The service uses **MD5 authentication** for production security:

```ini
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
```

### User Management
Users are defined in `services/pgbouncer/config/userlist.txt` with MD5 hashed passwords:
```
"username" "md5<hash>"
```

To generate MD5 hash for a password:
```bash
echo -n "detektor_passdetektor" | md5sum | awk '{print "md5"$1}'
```

### Connection Settings
- **Pool Mode**: Transaction
- **Max Client Connections**: 200
- **Default Pool Size**: 25
- **Port**: 6432

## Deployment

### Build Image
```bash
docker build -t ghcr.io/hretheum/detektr/pgbouncer:latest services/pgbouncer/
```

### Deploy via CI/CD
```bash
git add .
git commit -m "feat: add PgBouncer with MD5 authentication"
git push origin main
```

## Testing

### Test Connection
```bash
# Through PgBouncer (port 6432)
PGPASSWORD=detektor_pass psql -h nebula -p 6432 -U detektor -d detektor -c "SELECT 1;"

# Check pool status
PGPASSWORD=detektor_pass psql -h nebula -p 6432 -U detektor pgbouncer -c "SHOW POOLS;"
```

### Run Test Script
```bash
./services/pgbouncer/scripts/test-connection.sh
```

## Monitoring

### Health Check
```bash
curl http://nebula:6432/health || pg_isready -h nebula -p 6432 -U detektor
```

### View Statistics
```sql
-- Connect to pgbouncer database
PGPASSWORD=detektor_pass psql -h nebula -p 6432 -U detektor pgbouncer

-- Show pools
SHOW POOLS;

-- Show clients
SHOW CLIENTS;

-- Show servers
SHOW SERVERS;

-- Show statistics
SHOW STATS;
```

## Troubleshooting

### Authentication Failed
1. Check userlist.txt has correct MD5 hash
2. Verify password includes username in hash: `echo -n "passwordusername" | md5sum`
3. Check pgbouncer.ini auth_type is set to md5

### Connection Refused
1. Check PgBouncer is running: `docker ps | grep pgbouncer`
2. Verify port 6432 is exposed
3. Check network connectivity

### Pool Exhausted
1. Increase default_pool_size in pgbouncer.ini
2. Check for long-running transactions
3. Monitor connection usage with SHOW POOLS

## Security Notes
- **Never use** `auth_type = trust` in production
- Userlist.txt must have 600 permissions
- Regularly rotate database passwords
- Monitor failed authentication attempts in logs
# PgBouncer jest teraz używany jako bitnami/pgbouncer
