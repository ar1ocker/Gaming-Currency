package handlers

import (
	"context"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func CommandStartHandler(ctx context.Context, b *bot.Bot, update *models.Update) {
	b.SendMessage(ctx, &bot.SendMessageParams{ChatID: update.Message.Chat.ID, Text: "Hi, it is the postgres backup bot, if you see this message, it means we alive"})
}
