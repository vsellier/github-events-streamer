package main

import "testing"

func TestSave(t *testing.T) {
	event := `{"id":123456, "created_at": "2019-06-16T05:47:17Z"}`

	SaveEvent([]byte(event))

}
