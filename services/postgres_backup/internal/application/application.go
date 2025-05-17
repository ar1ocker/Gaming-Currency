package application

import (
	"context"
	"log"

	"postgres_backup/internal/backup"

	"github.com/go-telegram/bot"
)

func NewApplication(ctx context.Context, config *Config, bot *bot.Bot) *Application {
	app := &Application{backupExecutor: backup.NewBackupExecutor(), b: bot}

	app.backupChan = app.backupExecutor.CreatePeriodicBackupChan(ctx, config.backupInterval, config.postgres, config.backupDir)

	return app
}

func (app *Application) RunApplication(ctx context.Context) {
	app.b.RegisterHandler(bot.HandlerTypeMessageText, "start", bot.MatchTypeCommandStartOnly, app.CommandStartHandler)

	go app.BackupsProcessing(ctx)
	app.backupExecutor.RunBackupAfter(0)
}

func (app *Application) BackupsProcessing(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case result, ok := <-app.backupChan:
			if !ok {
				log.Println("The backup channel has been closed")
				return
			}

			log.Println(result.Err, result.FilePath)
		}
	}
}
