# BUILD

FROM golang:1.24-bookworm AS builder

WORKDIR /app/

COPY go.mod go.sum ./

RUN go mod download

COPY . .

RUN go build -o postgres_backup .

# APPLICATION

FROM debian:bookworm

WORKDIR /app/

ARG POSTGRES_VERSION=15

RUN apt update
RUN apt install -y --no-install-recommends "postgresql-client-${POSTGRES_VERSION}" ca-certificates

RUN update-ca-certificates

COPY --from=builder /app/postgres_backup .

ENTRYPOINT ["./postgres_backup"]
