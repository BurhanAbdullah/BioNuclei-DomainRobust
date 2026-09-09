FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BIONUCLEI_CHECKPOINT=/opt/models/bionuclei.pt \
    BIONUCLEI_JOB_DIR=/data/bionuclei-community-jobs

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY webapp ./webapp
COPY configs ./configs
COPY docs/RESEARCH_PROTOCOL.md docs/DATASETS.md docs/

RUN python -m pip install --upgrade pip \
    && python -m pip install -e ".[web]"

RUN mkdir -p /data/bionuclei-community-jobs /opt/models

EXPOSE 8000
CMD ["uvicorn", "webapp.community_app:app", "--host", "0.0.0.0", "--port", "8000"]
