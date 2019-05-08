FROM python:3.7

ARG WORK_DIR=/srv/gitlog

RUN useradd -md $WORK_DIR -s /bin/bash gitlog

USER gitlog

RUN python -m venv ${WORK_DIR}/python

ENV PATH=${WORK_DIR}/python/bin:${PATH}

RUN pip install --upgrade pip

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt
