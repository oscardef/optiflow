FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install sqlalchemy

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the item population script, then start the server
CMD ["/bin/sh", "-c", "python app/startup_populate_items.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
