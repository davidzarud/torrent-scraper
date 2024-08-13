# Use the official Python image from the DockerHub
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8888 available to the world outside this container
EXPOSE 8888

# Define environment variable
ENV FLASK_APP=app.py

# Run flask server
CMD ["flask", "run", "--host=0.0.0.0", "--port=8888"]
