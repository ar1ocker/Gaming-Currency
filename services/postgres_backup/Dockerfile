# BUILD

FROM golang:1.24-alpine AS builder

WORKDIR /app/

COPY go.mod go.sum ./

RUN go mod download

COPY . .

RUN go build -o postgres_backup .

# APPLICATION

FROM alpine:latest

WORKDIR /app/

ARG POSTGRES_VERSION=15

RUN apk --no-cache add "postgresql${POSTGRES_VERSION}-client"

COPY --from=builder /app/postgres_backup .

ENTRYPOINT ["./postgres_backup"]