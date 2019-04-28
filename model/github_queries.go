package model

import (
	"github.com/google/go-github/v24/github"
)

type ApiQuery struct {
	Type          QueryType          `json:"type"`
	ID            string             `json:"id"`
	ListOptions   github.ListOptions `json:"options"`
	ResponseTopic string             `json:"response_topic"`
}

type QueryType int

const (
	GetLastEvents QueryType = iota
	GetEventsPage
)

type ResponseStatus int

const (
	OK ResponseStatus = iota
	KO
)

type ApiResponse struct {
	ID      string         `json:"id"`
	Status  ResponseStatus `json:"status"`
	Payload []byte         `json:"payload"`
}
