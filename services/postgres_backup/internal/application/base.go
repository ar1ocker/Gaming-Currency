package application

import (
	"github.com/go-telegram/bot"
)

type Application struct{}

func (app *Application) RegisterHandlers(b *bot.Bot) {
	b.RegisterHandler(bot.HandlerTypeMessageText, "start", bot.MatchTypeCommandStartOnly, app.CommandStartHandler)
}
