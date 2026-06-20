FROM python:3.12-slim

RUN pip install uv

WORKDIR /app
COPY . .

# Install deps for all projects (shared requirements)
RUN uv pip install --system \
    fastapi>=0.128.0 \
    uvicorn>=0.40.0 \
    python-dotenv>=1.2.1 \
    qdrant-client>=1.16.2 \
    numpy>=2.4.1 \
    requests>=2.31

# Only install llama-cpp-python if running in local LLM mode
# For deployed/remote mode, skip it to keep the image small
ARG INSTALL_LLAMA_CPP=false
RUN if [ "$INSTALL_LLAMA_CPP" = "true" ]; then \
    uv pip install --system llama-cpp-python>=0.3.16; \
    fi

# Default: run project 1. Override with PROJECT env var.
ENV PROJECT=project1-procurement-search
ENV PORT=7777

CMD uvicorn app:app --host 0.0.0.0 --port ${PORT} --app-dir ${PROJECT}
