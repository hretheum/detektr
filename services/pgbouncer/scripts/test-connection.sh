#!/bin/bash
# Test PgBouncer connection with MD5 authentication

echo "Testing PgBouncer connection with MD5 authentication..."

# Test direct connection to PostgreSQL
echo "1. Testing direct PostgreSQL connection:"
PGPASSWORD=detektor_pass psql -h localhost -p 5432 -U detektor -d detektor -c "SELECT version();" || echo "Direct connection failed"

# Test connection through PgBouncer
echo -e "\n2. Testing PgBouncer connection:"
PGPASSWORD=detektor_pass psql -h localhost -p 6432 -U detektor -d detektor -c "SELECT version();" || echo "PgBouncer connection failed"

# Test PgBouncer admin interface
echo -e "\n3. Testing PgBouncer admin interface:"
PGPASSWORD=detektor_pass psql -h localhost -p 6432 -U detektor pgbouncer -c "SHOW POOLS;" || echo "PgBouncer admin interface failed"

# Test connection pooling
echo -e "\n4. Testing connection pooling (5 concurrent connections):"
for i in {1..5}; do
    (PGPASSWORD=detektor_pass psql -h localhost -p 6432 -U detektor -d detektor -c "SELECT pg_sleep(0.1), $i as connection_id;" &)
done
wait

echo -e "\n✅ Connection tests completed"
