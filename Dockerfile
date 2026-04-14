# Use a minimal Python base image
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install necessary system dependencies
RUN apk add --no-cache \
    ffmpeg \
    mkvtoolnix \
    gcc \
    musl-dev \
    libsndfile \
    python3-dev

# Copy requirements first (to leverage Docker caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Remove unnecessary build dependencies to reduce image size
RUN apk del gcc musl-dev python3-dev

# Copy the rest of the application
COPY . .

# Expose Flask port
EXPOSE 8888

# Set environment variables
ENV FLASK_APP=run:app

# Run Flask server
CMD ["flask", "run", "--host=0.0.0.0", "--port=8888"]