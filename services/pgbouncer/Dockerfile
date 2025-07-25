FROM pgbouncer/pgbouncer:1.22.1

# Copy configuration files
COPY config/pgbouncer.ini /etc/pgbouncer/pgbouncer.ini
COPY config/userlist.txt /etc/pgbouncer/userlist.txt

# Set proper permissions
RUN chmod 600 /etc/pgbouncer/userlist.txt && \
    chmod 644 /etc/pgbouncer/pgbouncer.ini && \
    chown pgbouncer:pgbouncer /etc/pgbouncer/userlist.txt /etc/pgbouncer/pgbouncer.ini

# Run as pgbouncer user
USER pgbouncer

# Start PgBouncer
CMD ["/usr/bin/pgbouncer", "/etc/pgbouncer/pgbouncer.ini"]
