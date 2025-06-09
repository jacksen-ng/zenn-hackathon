FROM python:3.12.6

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

ENV HOST=0.0.0.0
ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE ${PORT}

CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

