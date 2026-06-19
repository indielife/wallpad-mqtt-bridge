FROM python:3.12-slim

ENV LANG=C.UTF-8

WORKDIR /app

# Install Python package
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Addon config
COPY config.yaml ./
COPY translations/ ./translations/

# Entrypoint
COPY run.sh ./
RUN chmod +x run.sh

CMD ["./run.sh"]
