# Use an official lightweight Python base image
FROM python:3.12-slim

# Set Maintainer
LABEL maintainer="ian@icarey.net"

# Set environment variables to optimize Python behavior
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user with a specific UID and GID
ARG DEFAULT_UID=9911
ARG DEFAULT_GID=9911
RUN groupadd -g $DEFAULT_GID icad_dispatch && \
    useradd -m -u $DEFAULT_UID -g icad_dispatch icad_dispatch

# Switch to the non-root user for security
USER icad_dispatch

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /usr/src/app
COPY app.py /app
COPY lib /app/lib
COPY routes /app/routes
COPY static /app/static
COPY templates /app/templates
COPY requirements.txt /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Flask default port
EXPOSE 9911

# Default command to run the Flask app
CMD ["/home/icad_dispatch/.local/bin/gunicorn", "-b", "0.0.0.0:9911", "app:app"]
