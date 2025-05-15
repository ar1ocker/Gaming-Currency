package application

import (
	"postgres_backup/internal/backup"

	"github.com/go-telegram/bot"
)

type Application struct {
	backupChan     <-chan backup.BackupResult
	backupExecutor *backup.BackupExecutor
}

func (app *Application) RegisterHandlers(b *bot.Bot) {
	b.RegisterHandler(bot.HandlerTypeMessageText, "start", bot.MatchTypeCommandStartOnly, app.CommandStartHandler)
}

// func (app *Application) EnableBackup(ctx context.Context) {
// 	app.backupExecutor = &backup.BackupExecutor{}
// 	app.backupChan = app.backupExecutor.RunPeriodicBackup(ctx, time.Second*100, ...)
// }
