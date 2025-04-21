# Start from official Python image
FROM python:3.12-slim

# Set working dir
WORKDIR /

# Copy only requirements first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .
COPY .env .
# Expose port if needed
EXPOSE 8910

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8910"]
