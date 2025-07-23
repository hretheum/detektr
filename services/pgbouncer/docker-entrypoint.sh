#!/bin/sh
set -e

# Generate userlist.txt from environment variables
echo "\"${POSTGRES_USER:-detektor}\" \"${POSTGRES_PASSWORD}\"" > /etc/pgbouncer/userlist.txt
chmod 600 /etc/pgbouncer/userlist.txt

# Copy template if pgbouncer.ini doesn't exist
if [ ! -f /etc/pgbouncer/pgbouncer.ini ]; then
    cp /etc/pgbouncer/pgbouncer.ini.template /etc/pgbouncer/pgbouncer.ini
fi

# Start PgBouncer
exec pgbouncer /etc/pgbouncer/pgbouncer.ini
