# Use official Python slim image
FROM python:3.11-slim

# Disable .pyc and enable clean logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy all application files
COPY . .

# Expose Flask Gateway port
EXPOSE 8000

# Start the Flask Gateway
CMD ["python", "app.py"]
