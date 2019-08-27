import configparser
import requests
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

    github = None
    client_id = None
    client_secret = None

    consumer = None
    producer = None

    max_request_size = 1048576 * 5

    last_remaining_github_quota = None
    last_github_reset_time = None

    queries = {}

    def __init__(self):
        pass

    def query(self, url):
        r = requests.get(url)

        if r.status_code != 200:
            logger.error("Github response_code=%s", r.status_code)
            return None

        self.last_remaining_github_quota = r.headers['X-RateLimit-Remaining']
        self.last_github_reset_time = r.headers['X-RateLimit-Reset']
        return r

    def get_events(self, query, page=0):
        start = time.time() * 1000
        query_id = query['id']
        url = "https://api.github.com/events?client_id=%s&client_secret=%s&per_page=%s&page=%d" % (
            self.client_id, self.client_secret, 100, page)
        r = self.query(url)

        if r == None:
            self.logger.error("id=%s no response from github", query['id'])
            return

        end = time.time() * 1000

        self.logger.info(
            "id=%s query_type=get_events action=get page=%d duration_ms=%d", query_id, page, end-start)

        self.logger.debug(r.text)
        events = r.json()
        if page == 0:
            page2 = self.get_events(query, 1)
            if page2 != None:
                events.extend(page2)

            page3 = self.get_events(query, 2)
            if page3 != None:
                events.extend(page3)

        return events

    def connect_to_kafka(self, consumer_id):
        bootstrap_servers = self.config.get('kafka', 'bootstrap_servers')
        self.consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id='api_caller',
            client_id=consumer_id,
            session_timeout_ms=30000,
            value_deserializer=json.loads)

        self.consumer.subscribe(self.config.get('kafka', 'api_request_topic'))

        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                                      key_serializer=str.encode,
                                      max_request_size=self.max_request_size,
                                      compression_type='gzip',
                                      )

    def check_quota(self):
        self.logger.info("remaining quota: %s reset time: %s",
                         self.last_remaining_github_quota, self.last_github_reset_time)

    def wait_quota_reset(self):
        reset_time = self.github.rate_limiting_resettime()
        self.logger.info("reset time : %d", reset_time)

    def send_response(self, topic, key, response):
        start = time.time() * 1000
        self.logger.info(
            "Sending response to request_id=%s to topic=%s", key, topic)
        try:
            response = json.dumps(response).encode('utf-8')
            self.logger.info("request_id=%s response_lenth %d", key, len(response))
            future = self.producer.send(topic=topic, key=key,
                               value=response)
            future.error_on_callbacks = True
            self.producer.flush()
        except Exception as err:
            self.logger.error(
                "Error sending response on topic=%s for query=%s response:%s : %s", topic, key, response, err)

        # Block for 'synchronous' sends
        try:
            record_metadata = future.get(timeout=10)
        except Exception as err:
            # Decide what to do if produce request failed...
            self.logger.error(
                "Error sending the response to request_id=%s : %s", key, err)
            return None


        end = time.time() * 1000
        self.logger.info(
            "id=%s action=response duration_ms=%d", key, end-start)

    def perform_query(self, query):
        id = query['id']
        start = time.time() * 1000
        try:
            response = self.queries[query['type']](query, 0)
            # TODO check presency
            self.send_response(query['response_topic'], id, response)
            end = time.time() * 1000
            self.logger.info(
                "request_id=%s response sent after duration_ms=%d", id, end-start)
        except KeyError:
            self.logger.error("Unkown query type %d for %s",
                              query['type'], query)
            return
        except Exception as err:
            self.logger.error("Error on action %s : %s", query, err)
            return
        finally:
            self.check_quota()

    def connect_to_github(self, client_id, client_secret):
        self.logger.info("Using user %s to connect to github...", client_id)
        url = "https://api.github.com/rate_limit?client_id=%s&client_secret=%s" % (
            self.client_id, self.client_secret)
        self.query(url)
        self.check_quota()

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

        self.client_id = self.ghuser_config.get('github_user', 'client_id')
        self.client_secret = self.ghuser_config.get('github_user', 'client_secret')

        self.connect_to_github(
            self.client_id,
            self.client_secret)

        self.connect_to_kafka()

        self.logger.info("Waiting for messages on %s",
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
