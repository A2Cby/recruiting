FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY .env .
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8910   # FastAPI
EXPOSE 8501   # Streamlit

CMD ["/start.sh"]
