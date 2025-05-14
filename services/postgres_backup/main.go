package main

import (
	"context"
	"log"
	"os"
	"os/signal"

	"postgres_backup/internal/handlers"
	"postgres_backup/internal/middlwares"

	"github.com/go-telegram/bot"
)

func main() {
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancel()

	opts := []bot.Option{
		bot.WithMiddlewares(middlwares.LogMessagesMiddlware),
		bot.WithSkipGetMe(),
	}

	b, err := bot.New("7905186702:AAG8hwIWkDWFQKpwSxajdDnO5irEbe-zY0A", opts...)
	if err != nil {
		log.Fatal("Error on starting bot:", err)
	}

	me, err := b.GetMe(ctx)
	if err != nil {
		log.Fatal("Error on GetMe:", err)
	}

	b.RegisterHandler(bot.HandlerTypeMessageText, "/start", bot.MatchTypeCommandStartOnly, handlers.CommandStartHandler)

	log.Printf("Bot has been started: ID - %d, Username - https://t.me/%s\n", me.ID, me.Username)
	b.Start(ctx)
}
