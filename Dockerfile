FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories and set permissions
RUN mkdir -p data instance && \
    chmod 777 data && \
    chmod 777 instance

ENV FLASK_APP=app.py

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app", "--log-level", "debug"]