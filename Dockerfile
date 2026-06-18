#ARG BUILD_FROM="alpine:latest"
FROM python:3.12-slim

ENV LANG=C.UTF-8

# Set work directory
WORKDIR /app

# Package install
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Runtime scripts
COPY config.yaml run.sh ./
RUN chmod +x run.sh

CMD [ "./run.sh" ]
