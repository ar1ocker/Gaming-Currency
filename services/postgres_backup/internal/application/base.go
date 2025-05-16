package application

import (
	"context"
	"time"

	"postgres_backup/internal/backup"
	"postgres_backup/internal/postgres"

	"github.com/go-telegram/bot"
)

type Application struct {
	backupChan     <-chan backup.BackupResult
	backupExecutor *backup.BackupExecutor
}

type ApplicationConfig struct {
	postgres       postgres.PostgresOptions
	backupInterval time.Duration
	backupDir      string
	admins         []string
}

func NewApplication(ctx context.Context, config ApplicationConfig) *Application {
	app := &Application{backupExecutor: backup.NewBackupExecutor()}

	app.backupChan = app.backupExecutor.CreatePeriodicBackupChan(ctx, config.backupInterval, config.postgres, config.backupDir)

	return app
}

func (app *Application) RunHandlers(b *bot.Bot) {
	b.RegisterHandler(bot.HandlerTypeMessageText, "start", bot.MatchTypeCommandStartOnly, app.CommandStartHandler)
}
