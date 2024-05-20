ARG BUILD_FROM=BUILD_FROM=ghcr.io/hassio-addons/base:15.0.8
FROM $BUILD_FROM

ENV LANG C.UTF-8


# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY requirements.txt /

RUN \
  apk add --no-cache --virtual .build-dependencies \
    autoconf \
    automake \
    build-base \
    linux-headers \
    musl-dev \
    py3-pip \
    python3-dev \
  \
  && apk add --no-cache \
    py3-setuptools \
    python3 
RUN apk add --no-cache jq && \
  pip install -r requirements.txt --break-system-packages && \
  rm -rf /root/.cache

COPY monitor.py /
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
