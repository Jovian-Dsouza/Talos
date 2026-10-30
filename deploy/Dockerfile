# One image for the miner and the validator. Pass the module to run as the command:
#   docker run ... taunet python -m miner.main
#   docker run ... taunet python -m validator.main
FROM python:3.12-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml ./
COPY accounts ./accounts
COPY common ./common
COPY assets ./assets
COPY miner ./miner
COPY validator ./validator
RUN uv pip install --system --no-cache .
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "miner.main"]
