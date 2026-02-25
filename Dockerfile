FROM python:3.11-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY src/senzey_bots/pyproject.toml ./src/senzey_bots/
COPY src/ ./src/
COPY config/ ./config/

# Sync dependencies
RUN uv sync --frozen

ENTRYPOINT ["uv", "run", "streamlit", "run", "src/senzey_bots/ui/main.py", "--server.address=0.0.0.0"]
