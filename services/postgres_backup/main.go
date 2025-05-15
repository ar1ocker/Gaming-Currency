package main

import (
	"context"
	"log"
	"os"
	"os/signal"

	"postgres_backup/internal/application"
	"postgres_backup/internal/middlwares"

	"github.com/go-telegram/bot"
)

func main() {
	ctx, cancelContext := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancelContext()

	options := []bot.Option{
		bot.WithMiddlewares(middlwares.LogMessagesMiddlware),
		bot.WithSkipGetMe(),
	}

	b, err := bot.New("7905186702:AAG8hwIWkDWFQKpwSxajdDnO5irEbe-zY0A", options...)
	if err != nil {
		log.Fatal("Error on starting bot:", err)
	}

	app := application.Application{}

	app.RegisterHandlers(b)

	if err := logMe(ctx, b); err != nil {
		log.Fatal("Error on startup getMe:", err)
	}

	b.Start(ctx)
}

func logMe(ctx context.Context, b *bot.Bot) error {
	me, err := b.GetMe(ctx)
	if err != nil {
		return err
	}

	log.Printf("Bot has been started: ID - %d, Username - https://t.me/%s\n", me.ID, me.Username)

	return nil
}
