package main

import (
	"encoding/json"
	"fmt"
	"os"
	"time"

	log "github.com/sirupsen/logrus"

	"github.com/confluentinc/confluent-kafka-go-dev/kafka"
	"github.com/spf13/viper"
)

var (
	confKafkaServerURL   = "kafka_url"
	confEventsTopicName  = "events_topic"
	confGroupID          = "group_id"
	confWorkingDirectory = "working_directory"

	kafkaServer      string
	eventTopicName   string
	groupID          string
	workingDirectory string

	messageCounter chan int
	errorCounter   chan int
)

func loadConfig() {
	viper.SetConfigName("config")
	viper.AddConfigPath(".")
	viper.AutomaticEnv()
	err := viper.ReadInConfig()
	if err != nil {
		panic(fmt.Errorf("Fatal no config file: %s\n", err))
	}

	kafkaServer = viper.Get(confKafkaServerURL).(string)
	eventTopicName = viper.Get(confEventsTopicName).(string)
	groupID = viper.Get(confGroupID).(string)
	workingDirectory = viper.Get(confWorkingDirectory).(string)

	log.WithFields(log.Fields{
		"kafkaServer":       kafkaServer,
		"eventsTopicName":   eventTopicName,
		"groupID":           groupID,
		"working_directory": workingDirectory,
	}).Info("Configuration loaded")
}

func messageMonitorWatchdog(w chan int) {
	for {
		time.Sleep(2 * time.Second)
		w <- 1
	}
}

func messageMonitor(w chan int) {
	errors := 0
	messages := 0
	start := time.Now()

	for {
		select {
		case <-messageCounter:
			messages++
		case <-errorCounter:
			errors++
		case <-w:
			t := time.Now()
			elapsed := t.Sub(start)

			messagePerSecond := float64(messages) / elapsed.Seconds()
			errorsPerSecond := float64(errors) / elapsed.Seconds()

			log.WithFields(log.Fields{"elapsed": elapsed, "messagesPerSecond": messagePerSecond, "errorsPerSecond": errorsPerSecond, "messagesReceived": messages, "errorsDetected": errors}).Info("Ping received")

			messages = 0
			errors = 0
			start = time.Now()
		}
	}
}

func initMessageMonitor() {
	messageCounter = make(chan int)
	errorCounter = make(chan int)
	watchdog := make(chan int)

	go messageMonitorWatchdog(watchdog)
	go messageMonitor(watchdog)
}

func initWorkingDirectory(w string) {
	os.MkdirAll(workingDirectory, 0755)
}

// SaveEvent save a message
func SaveEvent(event []byte) {
	log.WithFields(log.Fields{"working_directory": workingDirectory}).Info("save massage")

	var eventJSON map[string]interface{}

	if err := json.Unmarshal(event, &eventJSON); err != nil {
		panic(err)
	}
	id := eventJSON["id"]
	date := eventJSON["created_at"]
	log.WithFields(log.Fields{"id": id, "date": date}).Info("decoded")

	parsedDate, err := time.Parse("2006-01-02T15:04:05Z", date.(string))
	if err != nil {
		log.WithFields(log.Fields{"date": date}).Error("Unable to parse date")
	}
	directoryName := parsedDate.Format("2006-01-02_15")
	log.WithFields(log.Fields{"parsedDate": parsedDate, "formatedDate": directoryName}).Info("done")

}

func main() {

	loadConfig()

	initWorkingDirectory(workingDirectory)

	initMessageMonitor()

	c, err := kafka.NewConsumer(&kafka.ConfigMap{
		"bootstrap.servers": kafkaServer,
		"group.id":          groupID,
		"auto.offset.reset": "earliest",
	})

	if err != nil {
		log.Fatal(err)
	}
	c.SubscribeTopics([]string{eventTopicName}, nil)

	for {
		msg, err := c.ReadMessage(-1)
		if err == nil {
			// log.WithFields(log.Fields{"partition": msg.TopicPartition.Partition}).Info("Message received")
			// fmt.Println(string(msg.Value))
			// os.Exit(0)
			SaveEvent(msg.Value)
			messageCounter <- 1
		} else {
			// The client will automatically try to recover from all errors.
			fmt.Printf("Consumer error: %v (%v)\n", err, msg)
			errorCounter <- 1
		}
	}

	c.Close()
}
