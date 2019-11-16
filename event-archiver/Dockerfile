FROM golang:1.13.4-stretch


RUN apt-get update && apt-get upgrade -y && apt-get install -y wget apt-transport-https \ 
  && wget -qO - https://packages.confluent.io/deb/5.3/archive.key | apt-key add - \
  && echo "deb [arch=amd64] https://packages.confluent.io/deb/5.3 stable main" > /etc/apt/sources.list.d/confluent.list

  # RUN apt-get update && apt-get install -y librdkafka-dev librdkafka1 libssl1.0.2 \
  #   && rm -rf /var/lib/apt /var/log/apt /var/cache/apt/ /var/cache/debconf /usr/share/doc

