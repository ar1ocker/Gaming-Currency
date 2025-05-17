package application

import (
	"time"

	"postgres_backup/internal/backup"
	"postgres_backup/internal/postgres"

	"github.com/go-telegram/bot"
)

type Application struct {
	backupChan     <-chan backup.BackupResult
	backupExecutor *backup.BackupExecutor
	b              *bot.Bot
}

type Config struct {
	postgres       postgres.PostgresOptions
	backupInterval time.Duration
	backupDir      string
	admins         []string
}
