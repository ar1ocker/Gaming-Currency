package application

import (
	"context"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func (app *Application) CommandStartHandler(ctx context.Context, b *bot.Bot, update *models.Update) {
	b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text: `Привет, это бот который делает бекап базы данных, если ты видишь это сообщение - значит он работает, а ты находишься в списке администраторов бота

Доступные команды:
/backup - немедленный запуск бекапа
/status - показ времени следующего бекапа
/list - показ списка файлов которые не были отправлены. При отсутствии ошибок - список пустой, все файлы отправлены и удалены с диска`,
	})
}
