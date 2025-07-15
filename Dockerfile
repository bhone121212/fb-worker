# Start with the base image
FROM docker.io/tiangolo/uwsgi-nginx-flask:python3.8

# Set working directory for requirements installation
WORKDIR /pysetup

# Install system dependencies required by psycopg2-binary and others
USER root
RUN apt-get update && apt-get install -y gcc libpq-dev nodejs && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY ./app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary folders
RUN mkdir -p /app/screenshots

# Switch to app directory
WORKDIR /app

# Copy app code
COPY ./app/ /app/

# Fix permissions (especially if using a non-root user later)
RUN chown -R www-data:www-data /app/screenshots

# Set timezone for the container
RUN ln -sf /usr/share/zoneinfo/Asia/Yangon /etc/localtime

# Copy start.sh script and make it executable
COPY start.sh /usr/src/app/start.sh
RUN chmod +x /usr/src/app/start.sh

# Set working directory for the app start
WORKDIR /usr/src/app

# Copy the rest of the project files
COPY . /app/ /usr/src/app

# Run the start script when container starts
CMD ["/usr/src/app/start.sh"]

