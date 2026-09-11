# Keep this runtime aligned with pyproject.toml. The digest prevents an
# unattended image refresh from changing Python or the base distribution.
FROM python:3.14.3-slim-bookworm@sha256:f21c0d5a44c56805654c15abccc1b2fd576c8d93aca0a3f74b4aba2dc92510e2 AS base

ENV  POETRY_VERSION=2.4.3 \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_HOME="/opt/poetry" \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  POETRY_NO_INTERACTION=1 \
  PYSETUP_PATH="/opt/pysetup" \
  VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


FROM base AS builder

RUN --mount=type=cache,target=/root/.cache \
  pip install "poetry==$POETRY_VERSION"

WORKDIR $PYSETUP_PATH

COPY ./poetry.lock ./pyproject.toml ./

RUN --mount=type=cache,target=$POETRY_HOME/pypoetry/cache \
  poetry install --only main --no-root


FROM base AS production

COPY --from=builder $VENV_PATH $VENV_PATH

COPY ./ /app/

WORKDIR /app
