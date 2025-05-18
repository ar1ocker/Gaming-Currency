package application

import (
	"context"
	"log"
	"os"
	"time"

	"postgres_backup/internal/backup"

	"github.com/go-telegram/bot"
)

func NewApplication(ctx context.Context, config *Config, bot *bot.Bot) *Application {
	app := &Application{backupExecutor: backup.NewBackupExecutor(), b: bot, config: config}

	os.MkdirAll(config.backupDir, 0o755)

	app.backupChan = app.backupExecutor.CreatePeriodicBackupChan(ctx, config.backupInterval, config.postgres, config.backupDir)

	return app
}

func (app *Application) RunApplication(ctx context.Context) {
	app.b.RegisterHandler(bot.HandlerTypeMessageText, "start", bot.MatchTypeCommandStartOnly, app.CommandStartHandler)
	app.b.RegisterHandler(bot.HandlerTypeMessageText, "backup", bot.MatchTypeCommandStartOnly, app.RunManualBackupHandler)
	app.b.RegisterHandler(bot.HandlerTypeMessageText, "list", bot.MatchTypeCommandStartOnly, app.ShowBackupsHandler)
	app.b.RegisterHandler(bot.HandlerTypeMessageText, "status", bot.MatchTypeCommandStartOnly, app.ShowNextRunTimeHandler)

	go app.BackupsProcessing(ctx)

	app.backupExecutor.RunBackupAfter(time.Second * 3)
}

func (app *Application) SendMessageToAllAdmins(ctx context.Context, message string) {
	errors := make([]error, 0)

	for _, chatID := range app.config.admins {
		_, err := app.b.SendMessage(ctx, &bot.SendMessageParams{ChatID: chatID, Text: message})
		if err != nil {
			errors = append(errors, err)
		}
	}

	if len(errors) > 0 {
		log.Println("Ошибки при отправке сообщений администраторам: ", errors)
	}
}
