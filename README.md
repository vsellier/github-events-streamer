# Github events follower

## Requirements

* A well configured python3 environment
* pip

## Install dependencies
On the project based directory:
```
$ pip install -r requirements.txt
```

TODO 
More info to come
TODO 

## Kafka topics creation
```
bin/kafka-topics.sh --zookeeper localhost:2181 --create --replication-factor 1 --partitions 1 --topic events-topic
bin/kafka-topics.sh --zookeeper localhost:2181 --create --replication-factor 1 --partitions 8 --topic github-queries
bin/kafka-topics.sh --zookeeper=localhost:2181 --create --partitions 1 --replication-factor 1 --config retention.ms=604800000 --topic github-response
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --partitions 1 --replication-factor 1 --config retention.ms=-1 --topic github-missed-event-periods
bin/kafka-topics.sh --list --zookeeper localhost:2181
```
