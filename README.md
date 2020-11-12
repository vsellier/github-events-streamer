# Github events follower

## Requirements

To run with docker (test environment)
* Docker
* docker-compose

## Start locally

* Copy ``docker-compose-dev.env`` to ``.env``
```
cp docker-compose-dev.env .env
```
* Adapt the ``.env`` file according your environment. Zookeeper and Kafka data are written by default on ``/tmp/gitlog``
* Create a file ``cmd/github_api_client/user1.cfg`` file with a 
```
[github_user]
client_id=<your user id>
client_secret=<your user secret>
```
* start the whole stack with
```
docker-compose up
```

## Appendix

## Kafka topics creation
```
./kafka-topics.sh --bootstrap-server localhost:9093 --create --replication-factor 1 --partitions 4 --config retention.ms=-1 --topic github-events
./kafka-configs.sh --zookeeper zookeeper:2181 --alter --add-config retention.ms=-1  --entity-name github-events --entity-type=topics

./kafka-topics.sh --bootstrap-server localhost:9093 --create --replication-factor 1 --partitions 8 --topic github-queries
./kafka-configs.sh --zookeeper zookeeper:2181 --alter --add-config retention.ms=-1  --entity-name github-queries --entity-type=topics

./kafka-topics.sh --bootstrap-server localhost:9093 --create --partitions 1 --replication-factor 1 --config retention.ms=-1 --topic github-response
./kafka-configs.sh --zookeeper zookeeper:2181 --alter --add-config retention.ms=-1  --entity-name github-response --entity-type=topics

./kafka-topics.sh --bootstrap-server localhost:9093 --create --partitions 1 --replication-factor 1 --config retention.ms=-1 --topic github-missed-event-periods
./kafka-configs.sh --zookeeper zookeeper:2181 --alter --add-config retention.ms=-1  --entity-name github-missed-event-periods --entity-type=topics
```

## Mirror
```
docker run -ti --rm --name mirror --net github-events-streamer_default --add-host kafka:192.168.30.20 --link github-events-streamer_kafka-mirror_1:kafka-mirror -v $PWD:/data github-events-streamer_kafka bash
./kafka-mirror-maker.sh  --consumer.config=/data/config/mirror/consumer.properties --producer.config=/data/config/mirror/producer.properties --num.streams=1 --whitelist '.*'

./kafka-consumer-groups.sh --bootstrap-server kafka:9093 --describe --group mirror-group
```

## Client
```
docker run -ti --rm --name kafka-client --add-host kafka-mirror:192.168.30.50  -v $PWD:/data github-events-streamer_kafka bash
```
### Display events
./kafka-console-consumer.sh --bootstrap-server kafka-mirror:9093 --from-beginning --group event-test --topic github-events  | jq -c '{id:.id,created:.created_at,type:.type,repo:.repo.name,actor:.actor.login}'
```


./kafka-configs.sh --zookeeper zookeeper:2181 --alter --add-config retention.ms=12960000000  --entity-name github-queries --entity-type=topics
./kafka-configs.sh --zookeeper zookeeper:2181 --alter --add-config retention.ms=12960000000  --entity-name github-queries --entity-type=topics
