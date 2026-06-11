#ARG BUILD_FROM="alpine:latest"
FROM python:3.12-slim

ENV LANG=C.UTF-8

# 필수 시스템 패키지만 설치 및 캐시 정리
RUN apt-get update && apt-get -y install jq && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Package install
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Runtime scripts
COPY run.sh makeconf.sh ./
RUN chmod +x run.sh makeconf.sh

CMD [ "./run.sh" ]
