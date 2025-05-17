package application

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"postgres_backup/internal/backup"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
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

	go app.BackupsProcessing(ctx)
	app.backupExecutor.RunBackupAfter(time.Second * 3)
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

			if result.Err != nil {
				log.Println(result.Err)
				app.SendMessageToAllAdmins(ctx, result.Err.Error())
				continue
			}

			fileData, err := os.ReadFile(result.FilePath)
			if err != nil {
				msg := fmt.Sprintf("Error on opening file %v, %v\n", result.FilePath, err)
				log.Println(msg)
				app.SendMessageToAllAdmins(ctx, msg)
			}

			for _, chatID := range app.config.backupChatIDs {
				_, err := app.b.SendDocument(
					ctx,
					&bot.SendDocumentParams{ChatID: chatID, Document: &models.InputFileUpload{
						Filename: filepath.Base(result.FilePath),
						Data:     bytes.NewReader(fileData),
					}})
				if err != nil {
					msg := fmt.Sprintf("Error on send file %s to chat %s", result.FilePath, chatID)
					log.Println(msg)
					app.SendMessageToAllAdmins(ctx, msg)
				}
				log.Printf("Sended backup %v to chat %v\n", filepath.Base(result.FilePath), chatID)
			}

			err = os.Remove(result.FilePath)
			if err != nil {
				msg := fmt.Sprintf("Error on delete log file %v", err)
				log.Println(msg)
				app.SendMessageToAllAdmins(ctx, msg)
			} else {
				log.Printf("Sended file %v has been deleted\n", result.FilePath)
			}
		}
	}
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
