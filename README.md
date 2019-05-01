# Github events follower

TODO 
More info to come
TODO 

## Kafka topics creation
```
bin/kafka-topics.sh --zookeeper localhost:2181 --create --replication-factor 1 --partitions 1 --topic events-topic
bin/kafka-topics.sh --zookeeper localhost:2181 --create --replication-factor 1 --partitions 8 --topic github-queries
bin/kafka-topics.sh --zookeeper=localhost:2181 --create --partitions 1 --replication-factor 1 --config retention.ms=604800000 --topic github-response
bin/kafka-topics.sh --zookeeper=localhost:2181 --create --partitions 4 --replication-factor 1 --config retention.ms=604800000 --topic github-events
bin/kafka-topics.sh --list --zookeeper localhost:2181
```
