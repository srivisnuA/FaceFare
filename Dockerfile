FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall -y opencv-python opencv-python-headless \
    && python -m pip install --no-cache-dir --no-deps opencv-python-headless==4.8.1.78

COPY . .

CMD ["sh", "-c", "gunicorn -w 1 --threads 100 -b 0.0.0.0:${PORT:-5000} app:app"]
