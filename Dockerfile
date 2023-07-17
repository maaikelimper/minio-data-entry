# Use a Python base image
FROM python:3.8-slim

# Install 'mc' (MinIO Client)
RUN apt-get update && apt-get install -y curl \
    && curl -o mc https://dl.min.io/client/mc/release/linux-amd64/mc \
    && chmod +x mc \
    && mv mc /usr/local/bin

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code to the working directory
COPY app.py .

# copy the script create-minio-users.py to the working directory
COPY create-minio-user.py .

# copy the templates folder to the working directory
COPY templates/ ./templates

# Expose the port on which the application will run
EXPOSE 5000

# Set the environment variable for Flask
ENV FLASK_APP=app.py

# Run the Flask application
CMD ["flask", "run", "--host=0.0.0.0"]
