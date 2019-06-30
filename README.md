# Github events follower

TODO 
More info to come
TODO 

## Kafka topics creation
```
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --replication-factor 1 --partitions 1 --topic events-topic
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --replication-factor 1 --partitions 8 --topic github-queries
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --partitions 1 --replication-factor 1 --config retention.ms=-1 --topic github-response
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --partitions 1 --replication-factor 1 --config retention.ms=-1 --topic github-missed-event-periods
bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --partitions 4 --replication-factor 1 --config retention.ms=-1 --topic github-events
bin/kafka-topics.sh --list --bootstrap-server localhost:9093
```



../../kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --delete --topic events-topic
../../kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --delete --topic github-queries
../../kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --delete --topic github-response
kafka-topics.sh --bootstrap-server localhost:9093 --delete --topic github-events2


../../kafka/bin/kafka-mirror-maker.sh --consumer.config consumer.properties --producer.config producer.properties --num.streams 2 --whitelist ".*"

../../kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --delete --topic github-missed-events
../../kafka/bin/kafka-topics.sh --bootstrap-server localhost:9093 --create --partitions 4 --replication-factor 1 --config retention.ms=1296000000 --topic github-events
kafka-topics.sh --bootstrap-server localhost:9093 --create --partitions 1 --replication-factor 1 --config retention.ms=-1 --topic github-missed-event-periods

kafka-topics.sh --bootstrap-server localhost:9093 --create --partitions 4 --replication-factor 1 --config retention.ms=-1 --topic github-events2
kafka-topics.sh --bootstrap-server localhost:9093 --create --partitions 1 --replication-factor 1 --config retention.ms=-1 --topic github-missed-event-periods2

## Kafka usefull command
### List topics
```
kafka-topics.sh --bootstrap-server localhost:9093 --list
```
### Display number of events on a given topic
```
kafka-run-class.sh kafka.tools.GetOffsetShell  --broker-list localhost:9093 --topic github-events
kafka-run-class.sh kafka.tools.GetOffsetShell  --broker-list localhost:9093 --topic github-response
kafka-run-class.sh kafka.tools.GetOffsetShell  --broker-list localhost:9093 --topic github-missed-event-periods
```
### List all consumer groups
```
kafka-consumer-groups.sh --bootstrap-server localhost:9093 --list
```
### Display consumer group status
```
kafka-consumer-groups.sh --bootstrap-server localhost:9093 --group reader --describe --all-topics
kafka-consumer-groups.sh --bootstrap-server localhost:9093 --group event_converter --describe --all-topics
kafka-consumer-groups.sh --bootstrap-server localhost:9093 --group missed-events --describe --all-topics
```
### Reset consumer offset
```
kafka-consumer-groups.sh --bootstrap-server localhost:9093 --group reader --execute --reset-offsets --to-earliest --all-topics
```
### Read topic messages
```
kafka-console-consumer.sh --bootstrap-server localhost:9093 --group reader --from-beginning --topic github-response --max-messages=1

kafka-console-consumer.sh --bootstrap-server localhost:9093  --partition 0 --from-beginning --topic github-events --max-messages=19349533 | jq -r '.id'> /srv/kafka/events-0.lst
kafka-console-consumer.sh --bootstrap-server localhost:9093  --partition 1 --from-beginning --topic github-events --max-messages=19338543| jq -r '.id'> /srv/kafka/events-1.lst
kafka-console-consumer.sh --bootstrap-server localhost:9093  --partition 2 --from-beginning --topic github-events --max-messages=19339803| jq -r '.id'> /srv/kafka/events-2.lst
kafka-console-consumer.sh --bootstrap-server localhost:9093  --partition 3 --from-beginning --topic github-events --max-messages=19344772| jq -r '.id'> /srv/kafka/events-3.lst
```


github-events:0:19349533
github-events:1:19338543
github-events:2:19339803
github-events:3:19344772

events -> 77372651
diff from raw -> 64398496

github-response:0:1050772

kafka-consumer-groups.sh --bootstrap-server localhost:9093 --group reader --execute --reset-offsets --to-earliest --all-topics
kafka-consumer-groups.sh --bootstrap-server localhost:9093 --describe --all-topics --group


Avant cleanup :
github-events:0:22 231 030
