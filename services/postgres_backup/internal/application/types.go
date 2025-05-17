package application

import (
	"postgres_backup/internal/backup"

	"github.com/go-telegram/bot"
)

type Application struct {
	backupChan     <-chan backup.BackupResult
	backupExecutor *backup.BackupExecutor
	b              *bot.Bot
	config         *Config
}
