# Github events follower

## Kafka topics creation
```
bin/kafka-topics.sh --zookeeper localhost:2181 --create --replication-factor 1 --partitions 1 --topic events-topic
bin/kafka-topics.sh --zookeeper localhost:2181 --create --replication-factor 1 --partitions 8 --topic github-queries
bin/kafka-topics.sh --zookeeper=localhost:2181 --create --partitions 1 --replication-factor 1 --config retention.ms=604800000 --topic github-response
bin/kafka-topics.sh --list --zookeeper localhost:2181
```

