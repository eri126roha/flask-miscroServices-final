# Base image
FROM python:3.11-slim

# Environment configuration
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the app source code
COPY . .

# Expose Flask port
EXPOSE 5000

# Run Kafka topic creation script, then start Flask app
CMD ["sh", "-c", "python kafka-setup.py && python app.py"]
