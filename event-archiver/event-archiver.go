package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"time"

	log "github.com/sirupsen/logrus"

	kafka "github.com/segmentio/kafka-go"
	_ "github.com/segmentio/kafka-go/gzip"
	_ "github.com/segmentio/kafka-go/snappy"
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

	messageReceived = 0
	messageWrote    = 0
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
			messageReceived++
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
func SaveEvent(event []byte) bool {
	log.WithFields(log.Fields{"working_directory": workingDirectory}).Debug("save message")

	var eventJSON map[string]interface{}

	if err := json.Unmarshal(event, &eventJSON); err != nil {
		panic(err)
	}
	id := eventJSON["id"]
	date := eventJSON["created_at"]
	log.WithFields(log.Fields{"id": id, "date": date}).Debug("decoded")

	parsedDate, err := time.Parse("2006-01-02T15:04:05Z", date.(string))
	if err != nil {
		log.WithFields(log.Fields{"date": date}).Error("Unable to parse date")
		return false
	}
	directoryName := parsedDate.Format("2006-01-02_15")
	log.WithFields(log.Fields{"parsedDate": parsedDate, "formatedDate": directoryName}).Debug("done")

	directory := workingDirectory + "/" + directoryName

	// Creating target directory
	if _, err := os.Stat(directory); err != nil {
		if os.IsNotExist(err) {
			log.WithFields(log.Fields{"directory": directory}).Info("Creating new directory")
			os.MkdirAll(directory, 0755)
		} else {
			log.WithFields(log.Fields{"error": err, "directory": directory}).Error("Error during directory test")
		}
	}

	// Saving file
	file := directory + "/" + id.(string) + ".json"
	err = ioutil.WriteFile(file, event, 0644)

	if err != nil {
		log.WithFields(log.Fields{"err": err, "file": file}).Error("Error writing event file")
		return false
	}
	messageWrote++
	return true
}

func main() {

	loadConfig()

	initWorkingDirectory(workingDirectory)

	initMessageMonitor()

	log.Info("Connecting to kafka broker...")
	c := kafka.NewReader(kafka.ReaderConfig{
		Brokers:        []string{kafkaServer},
		GroupID:        groupID,
		Topic:          eventTopicName,
		CommitInterval: time.Second,
		// "auto.offset.reset": "earliest",
	})
	log.Info("Connected...")

	// if err != nil {
	// 	log.Fatal(err)
	// }
	// c.SubscribeTopics([]string{eventTopicName}, nil)

	for {
		msg, err := c.ReadMessage(context.Background())
		if err == nil {
			// log.WithFields(log.Fields{
			// 	"partition": msg.Partition,
			// 	"offset":    msg.Offset,
			// }).Info("Message received")
			// fmt.Println(string(msg.Value))
			// os.Exit(0)
			messageCounter <- 1
			SaveEvent(msg.Value)
		} else {
			// The client will automatically try to recover from all errors.
			fmt.Printf("Consumer error: %v (%v)\n", err, msg)
			errorCounter <- 1
		}
	}

	c.Close()
}
