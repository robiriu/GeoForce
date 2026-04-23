# syntax=docker/dockerfile:1.7
# Multi-stage: build React dashboard, then serve it from FastAPI.

# ---------- Stage 1: dashboard build ----------
FROM node:20-bookworm-slim AS dashboard-build
WORKDIR /app/dashboard
COPY dashboard/package.json dashboard/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY dashboard/ ./
# Same-origin FastAPI in prod — routes are unprefixed (no dev /api rewrite).
ENV VITE_API_BASE=""
RUN npm run build

# ---------- Stage 2: Python runtime ----------
FROM python:3.11-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libgomp1 for torch; build-essential is dropped — we rely on wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only torch first (much smaller) then the rest.
COPY pyproject.toml ./
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.2.2 \
 && pip install --no-cache-dir \
        "numpy>=1.26,<2" "scipy>=1.12,<1.14" "iapws>=1.5.3" \
        "matplotlib>=3.8" "pyyaml>=6.0" "python-dotenv>=1.0" \
        "claude-agent-sdk>=0.1.0" "anthropic>=0.40.0" \
        "fastapi>=0.110" "uvicorn[standard]>=0.29" "sse-starlette>=2.0"

# Copy source.
COPY agent/ ./agent/
COPY solver/ ./solver/
COPY surrogate/ ./surrogate/
COPY tools/ ./tools/
COPY demo/ ./demo/
COPY app/ ./app/

# HF Spaces Docker SDK does not materialise LFS content in the build
# context — `surrogate/weights/geoforce_cnn_v1.1.pt` arrives as a pointer
# stub. Replace it with the real binary fetched from the Space's own
# public resolve URL (which redirects to Xet storage).
RUN f=surrogate/weights/geoforce_cnn_v1.1.pt && \
    if head -c 64 "$f" | grep -q '^version https://git-lfs'; then \
        echo "Replacing LFS pointer with real weights…" && \
        curl -fsSL -o "$f" \
          "https://huggingface.co/spaces/robiriu/geoforce/resolve/main/surrogate/weights/geoforce_cnn_v1.1.pt" && \
        ls -la "$f"; \
    fi

# Drop the built dashboard where FastAPI expects it.
COPY --from=dashboard-build /app/dashboard/dist ./dashboard/dist

EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD curl -fsS http://localhost:8765/health || exit 1

CMD ["uvicorn", "agent.api:app", "--host", "0.0.0.0", "--port", "8765"]
