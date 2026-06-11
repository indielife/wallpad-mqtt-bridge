#ARG BUILD_FROM="alpine:latest"
FROM python:3.12-slim

ENV LANG=C.UTF-8

# Install requirements for add-on
RUN apt-get update && apt-get -y install jq
RUN python3 -m pip install pyserial && \
        python3 -m pip install paho-mqtt

# Set work directory
WORKDIR /app

# Copy files
COPY *.py ./
COPY run.sh makeconf.sh ./

RUN chmod +x run.sh makeconf.sh

CMD [ "./run.sh" ]
