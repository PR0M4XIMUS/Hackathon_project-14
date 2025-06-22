FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "script.py"]