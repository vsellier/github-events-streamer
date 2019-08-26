FROM python:3.7

ARG WORK_DIR=/srv/gitlog
WORKDIR /srv/gitlog

RUN useradd -m -s /bin/bash gitlog \
  && apt-get update && apt-get install -y less jq

USER gitlog

ENV PATH=${HOME}/python/bin:${PATH}

COPY requirements.txt /requirements.txt

RUN python -m venv ${HOME}/python && . ${HOME}/python/bin/activate && pip install --upgrade pip && pip install -r /requirements.txt

USER root
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT /entrypoint.sh

RUN chmod a+x /entrypoint.sh

USER gitlog
