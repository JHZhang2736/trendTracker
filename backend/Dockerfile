FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy all source code first (needed for editable install)
COPY . .

# Install Python dependencies (editable, with dev extras)
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -e ".[dev]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
