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
    max_request_size = 1048576 * 5

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
            key_deserializer=self.key_deserializer,
            session_timeout_ms=30000,
            enable_auto_commit=False,
        )

        self.consumer.subscribe(self.github_events_topic_name)

        self.logger.info("Creating kafka producer...")
        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                                      compression_type='gzip',
                                      key_serializer=str.encode,
                                      max_request_size=self.max_request_size,
                                      )

    def shutdown(self):
        self.logger.info("Shutting down kafka consumer ...")
        self.consumer.commit()
        self.consumer.close()
        self.logger.info("Shutting down kafka producer...")
        self.producer.close()

    def send_event(self, key, event):
        try:
            event_json = json.dumps(event).encode('utf-8')
            self.producer.send(topic=self.event_topic_name,
                               key=event['id'],
                               value=event_json)
        except Exception as err:
            self.logger.error(
                "Error sending event on topic=%s event:%s : %s", self.event_topic_name, event_json, err)

    def convert_events(self, key, events):
        new_events = 0
        old_last_event_id = self.last_event_id
        old_last_event = self.last_event
        events_missed = self.last_event_id > -1
        # keep the older event of the current batch
        # to compute the missing event delay
        current_first_event = None
        first_event_id = None

        for event in events:
            # self.logger.info(event)
            # Initialising the older event during the first iteration
            if current_first_event == None:
                current_first_event = event

            event_id = int(event['id'])

            # find the smallest event id
            if event_id < int(current_first_event['id']):
                current_first_event = event

            # new event. increasing the counter
            if event_id > old_last_event_id:
                new_events += 1
                self.send_event(key, event)

            # compute the most recent event
            if event_id > self.last_event_id:
                self.last_event_id = event_id
                self.last_event = event

            # the bigger id of the previous batch is found
            # we have not missed any event
            if event_id <= old_last_event_id:
                events_missed = False
                break
            else:
                first_event_id = event_id

        if events_missed:
            self.logger.warning("request_id=%s event_count=%d some events missed between event_id=%d and event_id=%d max_missed=%d", key,
                                len(events), old_last_event_id, self.last_event_id, self.last_event_id - old_last_event_id)
        else:
            self.logger.info("request_id=%s new_events_count=%d event_count=%d first_event_id=%s last_event_id=%s",
                             key, new_events, len(events), first_event_id, self.last_event_id)

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
            self.logger.info("request_id=%s in progress ...", msg.key)

            events = msg.value

            self.convert_events(msg.key, events)
            self.consumer.commit()

            end = time.time() * 1000
            self.logger.info(
                "request_id=%s done in duration_ms=%d", msg.key, end-start)
        # self.consumer.commit()


if __name__ == "__main__":
    obj = EventConverter()
    try:
        obj.main()
    except KeyboardInterrupt:
        obj.shutdown()
        print("Exiting...")
