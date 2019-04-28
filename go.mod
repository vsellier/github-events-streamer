module github.com/vsellier/gitlog

go 1.12

require (
	github.com/confluentinc/confluent-kafka-go v1.0.0
	github.com/gofrs/uuid v3.2.0+incompatible
	github.com/google/go-github v17.0.0+incompatible
	github.com/google/go-github/v24 v24.0.1
	github.com/vsellier/gitlog/model v0.0.0-00010101000000-000000000000
)

replace github.com/vsellier/gitlog/model => ./model
