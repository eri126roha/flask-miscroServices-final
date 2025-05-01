# Base image
FROM python:3.11-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Working directory
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
# Copy and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy all source files (Flask app + kafka setup)
COPY . .

# Expose Flask port
EXPOSE 5000

# Run the Kafka topic setup script then launch the Flask app
CMD ["sh", "-c", "python kafka-setup.py && python app.py"]
