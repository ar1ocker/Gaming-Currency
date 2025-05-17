package main

import (
	"context"
	"log"
	"os"
	"os/signal"

	"postgres_backup/internal/application"
	"postgres_backup/internal/middlwares"

	"github.com/go-telegram/bot"
	"github.com/knadh/koanf/parsers/toml"
	"github.com/knadh/koanf/providers/file"
	"github.com/knadh/koanf/v2"
)

var k = koanf.New(".")

func main() {
	k.Load(file.Provider("config.toml"), toml.Parser())

	ctx, cancelContext := signal.NotifyContext(context.Background(), os.Interrupt)
	defer cancelContext()

	options := []bot.Option{
		bot.WithMiddlewares(middlwares.LogMessagesMiddlware),
		bot.WithSkipGetMe(),
	}

	b, err := bot.New(k.String("token"), options...)
	if err != nil {
		log.Fatal("Error on starting bot: ", err)
	}

	config := &application.Config{}

	_, err = config.LoadFromKoanf(k)
	if err != nil {
		log.Fatal(err)
	}

	app := application.NewApplication(ctx, config, b)

	app.RunApplication(ctx)

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
