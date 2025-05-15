package backupexecutor

import (
	"context"
	"fmt"
	"postgres_backup/internal/postgres"
	"time"
)

type BackupExecutor struct {
	ticker time.Ticker
}

func (executor *BackupExecutor) RunPeriodicBackup(ctx context.Context, duration time.Duration, host, port, user, password, dbName string) {
	executor.ticker = *time.NewTicker(duration)

	defer executor.ticker.Stop()

	for range executor.ticker.C {
		filePath := fmt.Sprintf("%d.backup", time.Now().Unix())

		postgres.DumpDatabase(host, port, user, password, dbName, filePath)
	}
}
