package application

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func (app *Application) RunManualBackupHandler(ctx context.Context, b *bot.Bot, update *models.Update) {
	alreadyRunned := app.backupExecutor.RunBackupAfter(0)

	var message string
	if alreadyRunned {
		message = "Бекап в данный момент в процессе подготовки"
	} else {
		message = "Запущен процесс бекапа"
	}

	b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   message,
	})
}

func (app *Application) ShowBackupsHandler(ctx context.Context, b *bot.Bot, update *models.Update) {
	dirEntries, err := os.ReadDir(app.config.backupDir)
	if err != nil {
		b.SendMessage(ctx, &bot.SendMessageParams{ChatID: update.Message.From.ID, Text: fmt.Sprintf("Ошибка при чтениии каталога: %v", err.Error())})
		return
	}

	if len(dirEntries) == 0 {
		b.SendMessage(ctx, &bot.SendMessageParams{ChatID: update.Message.From.ID, Text: "Файлов нет"})
		return
	}

	names := make([]string, len(dirEntries))
	for i, entry := range dirEntries {
		names[i] = entry.Name()
	}

	b.SendMessage(ctx, &bot.SendMessageParams{ChatID: update.Message.From.ID, Text: "Файлы:\n" + strings.Join(names, "\n")})
}

func (app *Application) ShowNextRunTimeHandler(ctx context.Context, b *bot.Bot, update *models.Update) {
	b.SendMessage(ctx, &bot.SendMessageParams{ChatID: update.Message.From.ID, Text: "Следующий запуск бекапа в: " + app.backupExecutor.NextRunTime.String()})
}
