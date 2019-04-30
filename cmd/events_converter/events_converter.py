import configparser
import json
from kafka import KafkaConsumer
from kafka import KafkaProducer
import logging
import logging.config
import sys
import time
import uuid


class EventConverter:
    logger = logging.getLogger()
    config = configparser.ConfigParser()

    consumer = None
    producer = None

    consumer_group_id = 'event_converter'
    github_events_topic_name = None
    event_topic_name = None
    last_event_id = -1
    last_event = None

    def key_deserializer(self, key):
        if key != None:
            return bytes.decode(key)
        else:
            return key

    def connect_to_kafka(self):
        bootstrap_servers = self.config.get('kafka', 'bootstrap_servers')
        self.logger.info("Kafka server(s): %s", bootstrap_servers)
        self.logger.info(
            "Creating kafka consumer with group_id=%s...", self.consumer_group_id)
        self.consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=self.consumer_group_id,
            value_deserializer=lambda m: json.loads(m, encoding='utf-8'),
            key_deserializer=self.key_deserializer
        )

        self.consumer.subscribe(self.github_events_topic_name)

        self.logger.info("Creating kafka producer...")
        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                                      #   compression_type='gzip',
                                      )

    def shutdown(self):
        self.logger.info("Shutting down kafka consumer ...")
        self.consumer.commit()
        self.consumer.close()
        self.logger.info("Shutting down kafka producer...")
        self.producer.close()

    def convert_events(self, key, events):
        new_event = 0
        self.logger.info("full messages=%s", json.dumps(events))
        for event in events:
            # if (event['id]'])
            self.logger.info("event=%s", json.dumps(event))
            self.logger.info(event['id'])

    def main(self):
        if len(sys.argv) != 2:
            self.print_usage()
            exit(1)

        # TODO check if the files exist
        config_file = sys.argv[1]

        print("Loading configuration from %s" % config_file)
        self.config.read(config_file)
        logging.config.fileConfig(config_file)

        self.github_events_topic_name = self.config.get(
            'kafka', 'api_response_topic')
        self.event_topic_name = self.config.get(
            'kafka', 'events_topic')

        self.connect_to_kafka()

        for msg in self.consumer:
            start = time.time() * 1000
            self.logger.info("Converting events of request_id=%s", msg.key)

            events = msg.value
            self.logger.info("number of events:%d", len(events))

            self.convert_events(msg.key, events)

            end = time.time() * 1000
            self.logger.info(
                "events of request_id=%s number_of_events=%d duration_ms=%d", msg.key, len(events), end-start)
        # self.consumer.commit()


if __name__ == "__main__":
    obj = EventConverter()
    try:
        obj.main()
    except KeyboardInterrupt:
        obj.shutdown()
        print("Exiting...")
