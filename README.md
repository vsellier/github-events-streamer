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
./kafka-topics.sh --bootstrap-server localhost:9093 --create --replication-factor 1 --partitions 8 --topic github-queries
./kafka-topics.sh --bootstrap-server localhost:9093 --create --partitions 1 --replication-factor 1 --config retention.ms=604800000 --topic github-response
./kafka-topics.sh --bootstrap-server localhost:9093 --create --partitions 1 --replication-factor 1 --config retention.ms=-1 --topic github-missed-event-periods
```
