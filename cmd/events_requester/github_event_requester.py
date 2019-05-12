import configparser
import json
from kafka import KafkaConsumer
from kafka import KafkaProducer
import logging
import logging.config
import sys
import time
import uuid


class EventRequester:
    logger = logging.getLogger()
    config = configparser.ConfigParser()

    consumer = None
    producer = None

    request_topic_name = None
    response_topic_name = None

    def print_usage(self):
        print("%s <config file path>" % sys.argv[0])

    def connect_to_kafka(self):
        bootstrap_servers = self.config.get('kafka', 'bootstrap_servers')
        self.consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id='event_requester',
            # value_deserializer=json.loads,
            key_deserializer=bytes.decode)

        self.consumer.subscribe(self.response_topic_name)

        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                                      #   compression_type='gzip',
                                      )

    def ask_for_events(self):
        request_id = str(uuid.uuid1())

        request = {}
        request['type'] = 0
        request['id'] = request_id
        request['response_topic'] = self.response_topic_name

        self.logger.info("sending request %s to topic %s",
                         request_id, self.request_topic_name)

        try:
            future = self.producer.send(
                self.request_topic_name, value=json.dumps(request).encode('utf-8'))
            future.error_on_callbacks = True
        except Exception as err:
            self.logger.error("Error sending request %s : %s", request_id, err)
            return None

        # Block for 'synchronous' sends
        try:
            record_metadata = future.get(timeout=10)
        except Exception as err:
            # Decide what to do if produce request failed...
            self.logger.error(
                "Error sending the request %s : %s", request, err)
            return None

        return request_id

    def wait_for_response(self, request_id, delay):
        self.logger.info(
            "Waiting for response of request_id=%s on topic=%s delay_s=%d", request_id, self.response_topic_name, delay)

        start = time.time() * 1000
        result = None
        while True:
            response = self.consumer.poll(timeout_ms=delay*1000, max_records=1)

            if len(response) == 0:
                self.logger.error(
                    "Response for request_id=%s not received after %ds", request_id, delay)
                break
            # only one message
            for key in response.keys():
                message = response[key][0]
            if message.key == request_id:
                self.logger.info(
                    "Response for request_id=%s received", request_id)
                result = message.value
                # self.consumer.commit()
                break
            else:
                self.logger.info("Message key=%s ignored", message.key)

        end = time.time() * 1000
        self.logger.info("request_id=%s response_received=%s duration_ms=%d",
                         request_id, result != None, end-start)
        return result

    def parse_response(self, response, last_event_id):
        new_last_event_id = last_event_id

        # print(len(response))

        for e in response:
            self.logger.error(e)
        # self.logger.info(response)
        # event = json.load(response[0])
        # print(event)

    def shutdown(self):
        self.logger.info("Shutting down kafka consumer ...")
        self.consumer.commit()
        self.consumer.close()
        self.logger.info("Shutting down kafka producer...")
        self.producer.close()

    def main(self):
        if len(sys.argv) != 2:
            self.print_usage()
            exit(1)

        # TODO check if the files exist
        config_file = sys.argv[1]

        print("Loading configuration from %s" % config_file)
        self.config.read(config_file)
        logging.config.fileConfig(config_file)

        self.response_topic_name = self.config.get(
            'kafka', 'api_response_topic')
        self.request_topic_name = self.config.get(
            'kafka', 'api_request_topic')
        self.event_topic_name = self.config.get(
            'kafka', 'events_topic')

        self.connect_to_kafka()

        while True:
            start = time.time() * 1000
            request_id = self.ask_for_events()
            if request_id != None:
                self.wait_for_response(request_id, 10)
            else:
                self.logger.info("No request id returned, skipping response wait")
            end = time.time() * 1000
            self.logger.info("cycle done duration_ms=%d", end-start)
            # time.sleep(1)


if __name__ == "__main__":
    obj = EventRequester()
    try:
        obj.main()
    except KeyboardInterrupt:
        obj.shutdown()
        print("Exiting...")
