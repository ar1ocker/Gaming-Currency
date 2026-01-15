package application

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

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
				msg := fmt.Sprintf("Error on opening file %v\n'%v'\n", result.FilePath, err)
				log.Println(msg)
				app.SendMessageToAllAdmins(ctx, msg)
				continue
			}

			for _, chatID := range app.config.backupChatIDs {
				_, err := app.b.SendDocument(ctx,
					&bot.SendDocumentParams{ChatID: chatID, Document: &models.InputFileUpload{
						Filename: filepath.Base(result.FilePath),
						Data:     bytes.NewReader(fileData),
					}})

				if err != nil {
					msg := fmt.Sprintf("Error on send file %s to chat %s", result.FilePath, chatID)
					log.Println(msg)
					log.Println(err)
					app.SendMessageToAllAdmins(ctx, msg)
				} else {
					log.Printf("Sended backup %v to chat %v\n", filepath.Base(result.FilePath), chatID)
				}
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
