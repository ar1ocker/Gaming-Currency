package middlwares

import (
	"context"
	"fmt"
	"log"
	"slices"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func MessagesOnlyFromIDs(IDs []string) func(bot.HandlerFunc) bot.HandlerFunc {
	return func(next bot.HandlerFunc) bot.HandlerFunc {
		return func(ctx context.Context, b *bot.Bot, update *models.Update) {
			if update.Message == nil {
				return
			}

			if slices.Contains(IDs, fmt.Sprintf("%d", update.Message.From.ID)) {
				next(ctx, b, update)
			} else {
				log.Printf("not admin with ID %v and username %v send message: %v", update.Message.From.ID, update.Message.From.Username, update.Message.Text)
			}
		}
	}
}
