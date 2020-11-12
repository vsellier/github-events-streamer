FROM ubuntu:18.04 as install

RUN apt-get update && apt-get install -y wget

ARG OPENJDK_VERSION=12.0.2_10

RUN if [ $(arch | grep -c arm) -gt 0 ]; then ARCH="arm"; else ARCH="x64"; fi; wget https://github.com/AdoptOpenJDK/openjdk12-binaries/releases/download/jdk-$(echo ${OPENJDK_VERSION} | sed 's/_/%2B/')/OpenJDK12U-jdk_${ARCH}_linux_hotspot_${OPENJDK_VERSION}.tar.gz -O /tmp/openjdk.tar.gz
RUN mkdir -p /usr/lib/jvm && tar xvzf /tmp/openjdk.tar.gz -C /usr/lib/jvm && mv /usr/lib/jvm/jdk-$(echo ${OPENJDK_VERSION} | tr '_' '+') /usr/lib/jvm/jdk

ARG KAFKA_VERSION=2.3.0
ARG KAFKA_SCALA_VERSION=2.12
RUN wget https://www-eu.apache.org/dist/kafka/${KAFKA_VERSION}/kafka_${KAFKA_SCALA_VERSION}-${KAFKA_VERSION}.tgz -O /tmp/kafka.tgz
RUN tar xvzf /tmp/kafka.tgz -C /opt && mv /opt/kafka_2.12-2.3.0 /opt/kafka

FROM ubuntu:18.04

RUN apt-get update && apt-get upgrade && apt-get install -y less jq && groupadd --gid 1000 kafka && useradd -d /opt/kafka --uid 1000 --gid 1000  kafka \
  && mkdir -p /usr/lib/jvm && mkdir /data && chown 1000:1000 /data

COPY --from=install /usr/lib/jvm/jdk /usr/lib/jvm/jdk
COPY --from=install --chown=1000:1000 /opt/kafka /opt/kafka

# Install java as default
RUN  for i in $(ls /usr/lib/jvm/jdk/bin); do update-alternatives --install /usr/bin/$i $i /usr/lib/jvm/jdk/bin/$i 10; done

COPY kafka.properties /etc/kafka.properties

USER kafka

WORKDIR /opt/kafka/bin

CMD [ "/opt/kafka/bin/kafka-server-start.sh", "/etc/kafka.properties"]
