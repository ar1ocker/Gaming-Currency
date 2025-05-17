package application

import (
	"context"
	"fmt"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func (app *Application) RunManualBackup(ctx context.Context, b *bot.Bot, update *models.Update) {
	alreadyRunned := app.backupExecutor.RunBackupAfter(0)

	b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   fmt.Sprintf("Backup runned: %v", alreadyRunned),
	})
}
