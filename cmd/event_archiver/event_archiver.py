import dateutil.parser
from dateutil.relativedelta import *
from datetime import *
import configparser
import json
from kafka import KafkaConsumer
from kafka import KafkaProducer
import logging
import logging.config
import os
import sys
import time
import uuid

class FilesManager:
    logger = logging.getLogger()

    indexes = {}

    checkpoint = datetime.now()
    checkpoint_interval = 1000
    checkpoint_count = 0
    closing_delay_mn = 15
    removing_delay_mn = 120
    working_dir = None
    existing = 0
    total = 0
    
    def __init__(self, workdir, producer, index_ready_topic_name):
        self.working_dir = workdir
        self.check_workdir()

        self.producer = producer
        self.index_ready_topic_name = index_ready_topic_name


    def check_workdir(self):
        try:
            os.mkdir(self.working_dir)
            self.logger.info("Working directory %s created", self.working_dir)
        except FileExistsError:
            self.logger.info("Working directory %s exists", self.working_dir)
            
    def check_index_directory(self, name):
        try:
            os.mkdir(self.working_dir + "/" + name)
            self.logger.info("Working directory %s created", name)
        except FileExistsError:
            self.logger.info("Working directory %s exists", name)
    
    def save_event(self, index, event):
        id = event["id"]
        created_date = event["created_at"]
        file_name = self.working_dir + "/" + index + "/" + id
        
        self.total = self.total + 1
        if os.path.exists(file_name):
            self.existing = self.existing + 1
            self.logger.debug("Event file %s already exists (%s), %d/%d", file_name, created_date, self.existing, self.total)

        f = open(file_name, "w+")
        f.write(json.dumps(event))
        f.close()

    def handle_event(self, message):
        event = message.value
        id = event["id"]
        created_date = event["created_at"]
        parsed_date = dateutil.parser.parse(created_date)
        new_file = False
        name = "{}{:02}{:02}_{:02}".format(parsed_date.year, parsed_date.month, parsed_date.day, parsed_date.hour)
        
        self.checkpoint_count = self.checkpoint_count + 1

        if name in self.indexes:
            if self.indexes[name]["closed"]:
                self.logger.warning("adding event to a closed index %s, reopening it", name)
                self.indexes[name]["closed"] = False

            # upgrade message count for the index
            count = self.indexes[name]["count"] + 1
            self.indexes[name]["count"] = count

            # log some processing informations
            if count % self.checkpoint_interval == 0:
                now = datetime.now()
                diff = now - self.checkpoint
                self.checkpoint = now
                msg_rate = self.checkpoint_count / diff.total_seconds()
                self.checkpoint_count = 0
                
                self.logger.info("%d event in file %s (%d indexes in progress) (%s msg/s)", count, name, len(self.indexes), msg_rate)
        else:
            self.logger.info("New index %s", name)
            self.check_index_directory(name)

            self.indexes[name]={}
            self.indexes[name]["count"] = 1
            self.indexes[name]["closed"] = False
        
        self.indexes[name]["updated_at"] =  datetime.now()

        self.check_index_status()

        self.save_event(name, event)

        return new_file

    def check_index_status(self):
        closing_limit = datetime.now()-relativedelta(minutes=self.closing_delay_mn)
        removing_limit = datetime.now()-relativedelta(minutes=self.removing_delay_mn)
        for name in list(self.indexes.keys()):
            # Closing index (send a compression event and mark as readonly)
            if self.indexes[name]["updated_at"] < closing_limit and self.indexes[name]["closed"] == False :
                self.notify_index_ready(name)

                self.logger.info("Closing directory %s event count : %d last update : %s", name, self.indexes[name]["count"], self.indexes[name]["updated_at"])
                self.indexes[name]["closed"]=True

            # Removing the index properties from the list to save memory
            if self.indexes[name]["updated_at"] < removing_limit :
                self.logger.info("Removing index properties %s event count : %d last update : %s", name, self.indexes[name]["count"], self.indexes[name]["updated_at"])
                self.indexes.pop(name)

    def notify_index_ready(self, index):
        self.logger.info("Notifying index %s is ready...", index)
        # Asynchronous by default
        future = self.producer.send(self.index_ready_topic_name, index.encode('utf-8'))

        try:
            future.get(timeout=10)
        except Exception as err:
            # Decide what to do if produce request failed...
            self.logger.error("Error notifying index %s is ready : %s", index, err)
            return False

        return True

class EventArchiver:
    logger = logging.getLogger()
    config = configparser.ConfigParser()
    
    consumer = None
    producer = None

    files_manager = None

    def key_deserializer(self, key):
        if key != None:
            return bytes.decode(key)
        else:
            return key
            
    def connect_to_kafka(self):
        bootstrap_servers = self.config.get('kafka', 'bootstrap_servers')
        self.logger.info("Kafka server(s): %s", bootstrap_servers)
        self.logger.info(
            "Creating kafka consumer of topic=%s with group_id=%s...", self.events_topic_name, self.consumer_group_id)
        self.consumer = KafkaConsumer(
            self.events_topic_name,
            bootstrap_servers=bootstrap_servers,
            group_id=self.consumer_group_id,
            value_deserializer=lambda m: json.loads(m, encoding='utf-8'),
            key_deserializer=self.key_deserializer,
            # enable_auto_commit=False,
        )

        self.consumer.subscribe(self.events_topic_name)
        self.producer = KafkaProducer(bootstrap_servers=bootstrap_servers,
                compression_type='gzip')

    def shutdown(self):
        self.logger.info("Shutting down kafka consumer ...")
        # self.consumer.commit()
        self.consumer.close()

    def print_usage(self):
        print("Usage :")
        print("\t%s <config file>" % sys.argv[0])

    def main(self):

        if len(sys.argv) != 2:
            self.print_usage()
            exit(1)

        # TODO check if the files exist
        config_file = sys.argv[1]

        print("Loading configuration from %s" % config_file)
        self.config.read(config_file)
        logging.config.fileConfig(config_file)

        try :
            self.events_topic_name = self.config.get(
                'kafka', 'events_topic')
            self.consumer_group_id = self.config.get('event_archiver', 'consumer_group')
            self.working_directory = self.config.get('event_archiver', 'working_directory')
            self.index_ready_topic_name = self.config.get('event_archiver', 'index_ready_topic')
        except configparser.NoOptionError as err:
            self.logger.error("Please check %s content : %s", config_file, err)
            exit(1)

        self.connect_to_kafka()

        self.files_manager = FilesManager(self.working_directory, self.producer, self.index_ready_topic_name)

        for event in self.consumer:
            self.files_manager.handle_event(event)
            # self.consumer.commit()

if __name__ == "__main__":
    obj = EventArchiver()
    try:
        obj.main()
    except KeyboardInterrupt:
        print("Exiting...")
    obj.shutdown()
