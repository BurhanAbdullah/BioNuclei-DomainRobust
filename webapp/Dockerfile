FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BIONUCLEI_CHECKPOINT=/opt/models/bionuclei.pt

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY webapp ./webapp
COPY configs ./configs
COPY docs/RESEARCH_PROTOCOL.md docs/DATASETS.md docs/

RUN python -m pip install --upgrade pip \
    && python -m pip install -e ".[web]"

EXPOSE 8000
CMD ["uvicorn", "webapp.app:app", "--host", "0.0.0.0", "--port", "8000"]
