FROM pgbouncer/pgbouncer:latest

# Copy configuration files as root (already root in base image)
COPY config/pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
COPY config/userlist.txt /etc/pgbouncer/userlist.txt

# Set proper permissions
RUN chmod 644 /etc/pgbouncer/pgbouncer.ini && \
    chmod 600 /etc/pgbouncer/userlist.txt

# Start PgBouncer
CMD ["/usr/bin/pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]
