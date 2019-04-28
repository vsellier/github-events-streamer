package main

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/gofrs/uuid"
	"github.com/vsellier/gitlog/model"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/google/go-github/v24/github"
)

var (
	githubQueriesTopic       = "github-queries"
	responseTopic            = "events-topic"
	maxPage                  = 2
	perPage                  = 100
	lastEventID        int64 = 0
)

func exit() {

}

func askLastEvents(p *kafka.Producer, page int) string {
	fmt.Println("Requesting last github events")
	uuid, err := uuid.NewV4()
	query := model.ApiQuery{Type: model.GetLastEvents, ID: uuid.String(), ResponseTopic: responseTopic,
		ListOptions: github.ListOptions{PerPage: perPage, Page: page}}
	fmt.Println(query)

	jq, err := json.Marshal(query)
	if err != nil {
		panic(err)
	}

	err = p.Produce(&kafka.Message{
		TopicPartition: kafka.TopicPartition{Topic: &githubQueriesTopic, Partition: kafka.PartitionAny},
		Value:          []byte(jq),
	}, nil)
	if err != nil {
		panic(err)
	}
	p.Flush(1 * 100)

	return uuid.String()
}

func listenForResponses(c *kafka.Consumer, p *kafka.Producer, currentPage int, requestID string) int64 {

	fmt.Println("Waiting for responses...")
	var msg *kafka.Message
	for {
		msg, err := c.ReadMessage(-1)
		if err != nil {
			// The client will automatically try to recover from all errors.
			fmt.Printf("Consumer error: %v (%v)\n", err, msg)
		}
		key := string(msg.Key)
		if key != requestID {
			fmt.Printf("Waiting for %s, ignoring response %s\n", requestID, key)
		} else {
			break
		}
	}
	// start := time.Now()

	response := model.ApiResponse{}
	err := json.Unmarshal(msg.Value, &response)
	if err != nil {
		fmt.Printf("Error unmarshalling response : %v \n", err)
	}
	fmt.Printf("Response receive : id=%s status=%d \n", response.ID, response.Status)
	if response.Status > model.OK {
		fmt.Printf("Error : %s (%v)\n", string(response.Payload), response)
		return lastEventID
	}

	events := []github.Event{}
	err = json.Unmarshal(response.Payload, &events)
	if err != nil {
		fmt.Printf("Error unmarshalling message : %v (%v)\n", err, msg.Value)
	}
	fmt.Printf("Number of events received : %d\n", len(events))

	var maxEvent int64 = 0
	var id int64
	var minEvent int64 = math.MaxInt64
	newEvents := 0
	found := false
	for _, event := range events {
		id, _ = strconv.ParseInt(*event.ID, 10, 64)
		if maxEvent < id {
			maxEvent = id
		}
		if minEvent > id {
			minEvent = id
		}
		if lastEventID == id {
			found = true
		}
		if lastEventID < id {
			// fmt.Printf("New Event %d : %s\n", id, *event.Type)
			newEvents = newEvents + 1
		}
	}
	fmt.Printf("New events : %d\n", newEvents)

	if found {
		fmt.Printf("*********** Event %d  found in the last response, current page %d\n", lastEventID, currentPage)
	} else {
		// fmt.Printf("Some event missed on page %d. last known id : %d first id of the batch : %d\n", currentPage, lastEventID, minEvent)
		if lastEventID > 0 && currentPage < maxPage {
			currentPage = currentPage + 1
			requestID := askLastEvents(p, currentPage)
			maxEvent = listenForResponses(c, p, currentPage, requestID)
		} else {
			fmt.Printf("************* Some events missed on page %d. last known id : %d first id of the batch : %d\n", currentPage, lastEventID, minEvent)
			lastEventID = maxEvent
			fmt.Printf("New last event id : %d\n", lastEventID)
		}
	}
	return maxEvent
}

func main() {
	signalChannel := make(chan os.Signal, 2)
	signal.Notify(signalChannel, os.Interrupt, syscall.SIGTERM)
	go func() {
		sig := <-signalChannel
		switch sig {
		case os.Interrupt:
			fmt.Println("Signal Interrupt received")
			exit()
			os.Exit(0)
		case syscall.SIGTERM:
			fmt.Println("Signal Sigterm received")
			exit()
			os.Exit(0)
		}
	}()

	// c, err := kafka.NewConsumer(&kafka.ConfigMap{
	// 	"bootstrap.servers": "localhost",
	// 	"group.id":          "myGroup",
	// 	"auto.offset.reset": "earliest",
	// })
	fmt.Println("Connecting to the kafka broker ...")
	p, err := kafka.NewProducer(&kafka.ConfigMap{"bootstrap.servers": "192.168.30.11"})
	if err != nil {
		panic(err)
	}

	defer p.Close()

	fmt.Println("Connected as producer")

	fmt.Println("Connection to kafka as a consumer...")
	c, err := kafka.NewConsumer(&kafka.ConfigMap{
		"bootstrap.servers": "192.168.30.11",
		"group.id":          "events-consumer11",
		"auto.offset.reset": "earliest",
	})
	if err != nil {
		fmt.Printf("Error trying to connect to kafka: %v\n", err)
		os.Exit(1)
	}
	c.SubscribeTopics([]string{responseTopic}, nil)

	// Delivery report handler for produced messages
	go func() {
		for e := range p.Events() {
			switch ev := e.(type) {
			case *kafka.Message:
				if ev.TopicPartition.Error != nil {
					fmt.Printf("Delivery failed: %v\n", ev.TopicPartition)
				} else {
					fmt.Printf("Delivered message to %v\n", ev.TopicPartition)
				}
			}
		}
	}()

	requestId := askLastEvents(p, 0)
	listenForResponses(c, p, 0, requestId)

	for {
		time.Sleep(1000 * time.Millisecond)

		requestId = askLastEvents(p, 0)
		listenForResponses(c, p, 0, requestId)
	}
	// Wait for message deliveries before shutting down
	fmt.Println("Sleep")
	p.Flush(5 * 1000)
	fmt.Println("End")
}
