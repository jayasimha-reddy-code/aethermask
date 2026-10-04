# ==========================================================================
#  AetherMask (CipherShift) :: air-gapped appliance image
# ==========================================================================
#  Stage 1 and 2 are the ONLY stages permitted network access, and only on the
#  build host. The final runtime image is started with network_mode: "none".
# ==========================================================================

# ---------- Stage 1: frontend bundle (local NPM artifacts, no CDN) --------
FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build:fast
# dist/ now contains a fully self-contained SPA: no remote fonts, no CDN.

# ---------- Stage 2: Python wheels ---------------------------------------
FROM python:3.12-slim-bookworm AS wheels
WORKDIR /wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --wheel-dir=/wheels/dist -r requirements.txt

# ---------- Stage 3: runtime (zero network) ------------------------------
FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="AetherMask" \
      org.opencontainers.image.description="Air-gapped semantic obfuscation and lossless de-anonymization platform" \
      org.opencontainers.image.version="2.1.0" \
      com.aethermask.airgap="enforced" \
      com.aethermask.egress="none"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_INDEX=1 \
    # Hard offline switches for any library that might probe a network
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    NO_PROXY="*" \
    AETHERMASK_HOST=0.0.0.0 \
    AETHERMASK_PORT=8000 \
    AETHERMASK_BLOCK_EGRESS=1 \
    AETHERMASK_STATIC_DIR=/app/frontend/dist

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin aether

WORKDIR /app

# Install strictly from the locally-built wheelhouse. --no-index guarantees
# that no package index is ever contacted, even if a network existed.
COPY --from=wheels /wheels/dist /tmp/wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/tmp/wheels -r requirements.txt \
    && rm -rf /tmp/wheels /root/.cache

COPY core/ /app/core/
COPY api/ /app/api/
COPY cli/ /app/cli/
COPY --from=frontend /build/dist /app/frontend/dist

RUN mkdir -p /app/vault_out /app/workspace \
    && chown -R aether:aether /app

USER aether
EXPOSE 8000

# Loopback-only healthcheck: works with network_mode "none".
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python3 -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=4).status==200 else 1)"

CMD ["python3", "-m", "uvicorn", "api.server:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
