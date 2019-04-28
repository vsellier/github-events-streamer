package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	"github.com/google/go-github/v24/github"
	"github.com/vsellier/gitlog/model"
)

var (
	userAgent         = "Github events streamer"
	githubApiUrl      = "https://api.github.com"
	eventsEndpointUrl = githubApiUrl + "/events"
)

func unsubscribe(c *kafka.Consumer) {
	fmt.Printf("Closing consumer")

	err := c.Unsubscribe()
	if err != nil {
		fmt.Println(err)
	}
}

func publishResponse(p *kafka.Producer, query model.ApiQuery, response model.ApiResponse) {
	response.ID = query.ID

	jq, err := json.Marshal(response)
	if err != nil {
		panic(err)
	}

	err = p.Produce(&kafka.Message{
		TopicPartition: kafka.TopicPartition{Topic: &query.ResponseTopic, Partition: kafka.PartitionAny},
		Value:          []byte(jq),
	}, nil)
	if err != nil {
		fmt.Printf("Error sending response for query id=%s %v", query.ID, err)
	} else {
		p.Flush(1 * 100)
	}
}

func computeGithubQuota(response *http.Response) {
	limit, _ := strconv.Atoi(response.Header.Get("X-RateLimit-Limit"))
	remaining, _ := strconv.Atoi(response.Header.Get("X-RateLimit-Remaining"))
	pollInterval, _ := strconv.Atoi(response.Header.Get("X-Poll-Interval"))
	reset, _ := strconv.ParseInt(response.Header.Get("X-RateLimit-Reset"), 10, 64)
	delayBeforeReset := time.Now().Sub(time.Unix(reset, 0))

	fmt.Printf("limit=%d remaining=%d reset=%d delayBeforeReset=%f interval=%d\n", limit, remaining, reset, delayBeforeReset.Seconds(), pollInterval)
}

func getLastEvents(c *github.Client, o github.ListOptions) model.ApiResponse {
	events, response, err := c.Activity.ListEvents(context.Background(), &o)

	fmt.Printf("Limits : %v\n", response.Rate)

	reply := model.ApiResponse{}
	if err != nil {
		reply.Status = model.KO
		defer response.Body.Close()
		body, _ := ioutil.ReadAll(response.Body)
		reply.Payload = body
		fmt.Printf("Error from github : %v\n", err)
	} else {
		json, err := json.Marshal(events)
		if err != nil {
			fmt.Printf("Error converting events to json : %v\n", err)
			reply.Status = model.KO
		}
		reply.Payload = json
	}

	return reply
}

func performQuery(c *github.Client, q model.ApiQuery) model.ApiResponse {
	switch q.Type {
	case model.GetLastEvents:
		fmt.Println("GetLastEvent query received")
		response := getLastEvents(c, q.ListOptions)
		return response
	case model.GetEventsPage:
		fmt.Println("GetEventPage query received")
	}
	return model.ApiResponse{}
}

func main() {
	fmt.Println("Connection to kafka as a consumer...")
	c, err := kafka.NewConsumer(&kafka.ConfigMap{
		"bootstrap.servers": "192.168.30.11",
		"group.id":          "github_query_consumer",
		"auto.offset.reset": "earliest",
	})
	if err != nil {
		fmt.Printf("Error trying to connect to kafka: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("Connection to kafka as a producer...")
	p, err := kafka.NewProducer(&kafka.ConfigMap{"bootstrap.servers": "192.168.30.11"})
	if err != nil {
		panic(err)
	}

	signalChannel := make(chan os.Signal, 2)
	signal.Notify(signalChannel, os.Interrupt, syscall.SIGTERM)
	go func() {
		sig := <-signalChannel
		switch sig {
		case os.Interrupt:
			fmt.Println("Signal Interrupt received")
			unsubscribe(c)
			os.Exit(0)
		case syscall.SIGTERM:
			fmt.Println("Signal Sigterm received")
			unsubscribe(c)
			os.Exit(0)
		}
	}()

	fmt.Println("Connecting to github...")
	// tp := github.BasicAuthTransport{
	// 	Username: strings.TrimSpace("eventlogger01"),
	// 	Password: strings.TrimSpace("389f46b7c1c52d80e7d2b7cd562b2b4be4865c23"),
	// }

	tp := &github.UnauthenticatedRateLimitedTransport{
		ClientID:     "aa19a56fbdfeb97b8b70",
		ClientSecret: "d3575ecaf7c9e4cd45882d7fa440187e2ef45e07",
	}
	githubClient := github.NewClient(tp.Client())

	// checking authentication
	_, response, err := githubClient.Activity.ListEvents(context.Background(), nil)
	fmt.Printf("Limits : %v\n", response.Rate)
	if err != nil {
		fmt.Printf("Authentication failed : %v\n", err)
		os.Exit(1)
	}

	fmt.Println("Authentication done")
	fmt.Println("Waiting for events...")

	c.SubscribeTopics([]string{"github-queries"}, nil)

	for {
		msg, err := c.ReadMessage(-1)
		if err != nil {
			// The client will automatically try to recover from all errors.
			fmt.Printf("Consumer error: %v (%v)\n", err, msg)
		}
		start := time.Now()

		query := model.ApiQuery{}
		err = json.Unmarshal(msg.Value, &query)
		if err != nil {
			fmt.Printf("Error unmarshalling messqge : %v (%v)\n", err, msg.Value)
		}
		fmt.Printf("Request received (p=%d v=%s)\n", msg.TopicPartition.Partition, string(msg.Value))

		queryStart := time.Now()
		response := performQuery(githubClient, query)
		queryEnd := time.Now()

		responseStart := time.Now()
		publishResponse(p, query, response)
		responseEnd := time.Now()

		duration := responseEnd.Sub(start)
		queryDuration := queryEnd.Sub(queryStart)
		responseDuration := responseEnd.Sub(responseStart)
		fmt.Printf("Request done id=%s duration=%f query_duration=%f response_duration=%f\n", query.ID, duration.Seconds(), queryDuration.Seconds(), responseDuration.Seconds())
	}

	fmt.Println("Closing consumer")
	c.Close()
}
