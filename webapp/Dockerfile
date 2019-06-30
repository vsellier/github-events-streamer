FROM python:3.7

ENV WORK_DIR=/srv/gitlog

RUN apt-get update && apt-get upgrade -y && apt-get install -y git

RUN useradd -md $WORK_DIR -s /bin/bash gitlog

ENV PATH=/opt/python/bin:${PATH}

RUN mkdir -p ${WORK_DIR} \
    && python -m venv /opt/python \
    && pip install --upgrade pip \
    && pip install Django 
    # channels

USER gitlog

WORKDIR ${WORK_DIR}/webapp/web

COPY requirements.txt /tmp/requirements
#RUN cat /tmp/requirements | xargs -t pip install 
