import configparser
from github import Github
import json
from kafka import KafkaConsumer
from kafka import KafkaProducer
import logging
import logging.config
import sys
import time

import pdb


class GithubApiQueryConsumer:
    logger = logging.getLogger()
    config = configparser.ConfigParser()
    # TODO check if possible to use the same parser
    ghuser_config = configparser.ConfigParser()

    github = 0
    github_user = 0

    consumer = None
    producer = None

    queries = {}

    def __init__(self):
        pass

    def get_events(self, query):
        start = time.time() * 1000
        iterable_events = self.github_user.get_events()

        events = []
        for github_event in iterable_events:
            event = {}
            event['actor']=github_event.actor
            event['payload']=github_event.payload
            events.append(event)

        self.logger.debug(events)

        end = time.time() * 1000

        self.logger.info("id=%s query_type=get_events action=get duration_ms=%d", query['id'], end-start)
        return events

    def connect_to_kafka(self, consumer_id):
        bootstrap_servers = self.config.get('kafka', 'bootstrap_servers')
        self.consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id='api_caller',
            client_id=consumer_id,
            value_deserializer=json.loads)

        self.consumer.subscribe(self.config.get('kafka', 'api_request_topic'))

        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                                      key_serializer=str.encode,
                                      #   compression_type='gzip',
                                      )

    def check_quota(self):
        quota = self.github.get_rate_limit()
        self.logger.info("quota: %s", quota)

    def wait_quota_reset(self):
        reset_time = self.github.rate_limiting_resettime()
        self.logger.info("reset time : %d", reset_time)

    def send_response(self, topic, key, response):
        start = time.time() * 1000
        self.logger.info("Sending response to request_id=%s to topic=%s", key, topic)
        try:
            self.producer.send(topic=topic, key=key, value=json.dumps(response).encode('utf-8'))
        except Exception as err:
            self.logger.error("Error sending response on topic=%s for query=%s response:%s : %s", topic, key, response, err)
        end = time.time() * 1000
        self.logger.info("id=%s action=response duration_ms=%d", key, end-start)


    def perform_query(self, query):
        try:
            response = self.queries[query['type']](query)
            # TODO check presency
            self.send_response(query['response_topic'], query['id'], response)
        except KeyError:
            self.logger.error("Unkown query type %d for %s",
                              query['type'], query)
            return
        except Exception as err:
            self.logger.error("Error on action %s : %s", query, err)
            return
        finally:
            self.check_quota()

    def connect_to_github(self, login, password, client_id, client_secret):
        self.logger.info("Using user %s to connect to github...", login)
        self.github = Github(login_or_token=login, password=password,
                             client_id=client_id, client_secret=client_secret, per_page=100)
        rate = self.github.get_rate_limit()
        self.logger.info(rate)
        # pdb.set_trace()
        self.github_user = self.github.get_user()

    def print_usage(self):
        print("%s <config file path> <github config file path>" % sys.argv[0])

    def register_supported_queries(self):
        self.logger.info("Register get_events")
        self.queries[0] = self.get_events

    def shutdown(self):
        self.logger.info("Shutting down kafka consumer ...")
        self.consumer.commit()
        self.consumer.close()
        self.logger.info("Shuting down kafka producer...")
        self.producer.close()

    def main(self):
        if len(sys.argv) != 3:
            self.print_usage()
            exit(1)

        # TODO check if the files exist
        config_file = sys.argv[1]
        gh_user_config = sys.argv[2]

        print("Loading configuration from %s" % config_file)
        self.config.read(config_file)
        logging.config.fileConfig(config_file)

        self.register_supported_queries()

        self.logger.info(
            "Loading github user credential from %s", gh_user_config)
        self.ghuser_config.read(gh_user_config)

        github_user = self.ghuser_config.get('github_user', 'login')
        self.connect_to_github(
            github_user,
            self.ghuser_config.get('github_user', 'password'),
            self.ghuser_config.get('github_user', 'client_id'),
            self.ghuser_config.get('github_user', 'client_secret'))

        self.connect_to_kafka(github_user)

        self.logger.info("Waitting for messages on %s",
                         self.config.get('kafka', 'api_request_topic'))

        for msg in self.consumer:
            # logger.debug(msg)
            self.logger.info("Message received on partition %d", msg.partition)

            # try:
            #     query = json.loads(msg.value.decode("utf-8"))
            # except AttributeError as err:
            #     logger.error("Unable to deserialize %s : %s", raw_msg, err)
            #     continue

            self.perform_query(msg.value)


if __name__ == "__main__":
    obj = GithubApiQueryConsumer()
    try:
        obj.main()
    except KeyboardInterrupt:
        obj.shutdown()
        print("Exiting...")
