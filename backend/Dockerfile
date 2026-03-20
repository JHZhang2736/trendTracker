FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifest first — this layer is cached until pyproject.toml changes
COPY pyproject.toml .
# Create a minimal stub so setuptools can resolve the package metadata without full source
RUN mkdir -p app && touch app/__init__.py

# Install production dependencies only — dev tools (ruff, pytest, black) not needed in container
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple "."

# Now copy the real source code — changes here do NOT invalidate the pip cache layer above
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
