FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/IronMan_Recovery/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/IronMan_Recovery/requirements.txt

COPY . /app/IronMan_Recovery

RUN python -m unittest IronMan_Recovery.test_recovery -v \
    && useradd --create-home --uid 10001 ironman

USER 10001

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn IronMan_Recovery.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
