FROM python:3.11-alpine

# Create non-root user and switch to it
RUN adduser -D -s /sbin/nologin vibingway
USER vibingway

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --user -r /tmp/requirements.txt

# Copy app
COPY . /app

# Run app
CMD ["python3", "launch.py"]
