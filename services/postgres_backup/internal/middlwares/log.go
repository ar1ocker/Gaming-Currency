package middlwares

import (
	"context"
	"log"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func LogMessagesMiddlware(next bot.HandlerFunc) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		if update.Message != nil {
			log.Printf("ID: %d, Username: @%s, Message: %s", update.Message.From.ID, update.Message.From.Username, update.Message.Text)
		}
		next(ctx, b, update)
	}
}
