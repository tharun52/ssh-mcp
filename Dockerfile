FROM python:3.12-alpine AS builder

RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-alpine

WORKDIR /app
COPY --from=builder /install /usr/local
COPY aws/ aws/
COPY tools/ tools/
COPY config.py connection.py server.py ./

RUN mkdir -p /transfers

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "server.py"]
