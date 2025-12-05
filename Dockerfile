FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install cron and git
RUN apt-get update && apt-get install -y cron git tzdata && rm -rf /var/lib/apt/lists/*

# Configure git user for commits
RUN git config --global user.email "backup@bot.com" && \
    git config --global user.name "Backup Bot"

COPY src/ src/

# Copy crontab file to the cron.d directory
COPY crontab /etc/cron.d/backup-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/backup-cron

# Apply cron job
RUN crontab /etc/cron.d/backup-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Create directory for backups
RUN mkdir -p /backups

# Set environment variable for backup directory (can be overridden)
ENV BACKUP_DIR=/backups

# Run the command on container startup
# We dump env vars to /etc/environment so cron can see them
CMD printenv > /etc/environment && cron && tail -f /var/log/cron.log
