FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    BIONUCLEI_CHECKPOINT=/opt/models/bionuclei.pt \
    BIONUCLEI_JOB_DIR=/data/bionuclei-community-jobs

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY webapp ./webapp
COPY configs ./configs
COPY docs/RESEARCH_PROTOCOL.md docs/DATASETS.md docs/

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision \
    && python -m pip install --no-cache-dir -e ".[web]"

RUN mkdir -p /data/bionuclei-community-jobs /opt/models

EXPOSE 8000
CMD ["uvicorn", "webapp.community_app:app", "--host", "0.0.0.0", "--port", "8000"]
