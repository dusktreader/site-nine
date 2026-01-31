# ==== Base stage: install base dependencies ===========================================================================
FROM ubuntu:24.04 AS base

RUN groupadd -g 5000 h-queue \
  && useradd -d /home/h-queue -m -u 5000 -g 5000 h-queue

ENV PATH="/venv/bin:$PATH"

RUN mkdir /app && \
  chown h-queue:h-queue /app && \
  mkdir /venv && \
  chown h-queue:h-queue /venv && \
  mkdir /py-bin && \
  chown h-queue:h-queue /py-bin


# ==== Build stage: build the app ======================================================================================
FROM base AS build

USER h-queue
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/venv \
    UV_PYTHON_INSTALL_DIR=/py-bin

COPY --from=ghcr.io/astral-sh/uv:0.6.6 /uv /uvx /bin/
RUN uv python install 3.14 && \
    ln -s $(uv python find 3.14) /py-bin/python

WORKDIR /app

# This is so dumb, but uv won't build if the README isn't there
RUN touch /app/README.md

RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=src/,target=src/ \
    uv sync \
        --locked \
        --no-dev \
        --no-editable


# ==== Final stage: copy venv and run ==================================================================================
FROM base AS final

ENV PATH="/venv/bin:/py-bin:$PATH"

COPY --from=build --chown=h-queue:h-queue /venv /venv
COPY --from=build --chown=h-queue:h-queue /py-bin /py-bin

# Smoke test!
RUN python -Ic 'import h_queue'
