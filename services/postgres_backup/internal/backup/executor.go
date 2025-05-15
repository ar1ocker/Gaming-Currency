package backup

import (
	"context"
	"fmt"
	"time"

	"postgres_backup/internal/postgres"
)

func (executor *BackupExecutor) RunPeriodicBackup(ctx context.Context, interval time.Duration, postgresOptions *postgres.PostgresOptions, backupDir string) <-chan BackupResult {
	executor.timer = time.NewTimer(time.Second * 10)
	resultChan := make(chan BackupResult)

	go func() {
		defer close(resultChan)
		defer executor.timer.Stop()

		for {
			select {
			case <-ctx.Done():
				return
			case <-executor.timer.C:
				startTime := time.Now()

				result := executor.DumpDatabase(postgresOptions, backupDir)

				elapsed := time.Since(startTime)
				nextInterval := interval - elapsed

				if nextInterval < 0 {
					nextInterval = 0
				}

				executor.timer.Reset(nextInterval)

				select {
				case resultChan <- result:
				case <-ctx.Done():
					return
				}
			}
		}
	}()

	return resultChan
}

func (executor *BackupExecutor) DumpDatabase(postgresOptions *postgres.PostgresOptions, backupDir string) BackupResult {
	filePath := fmt.Sprintf("%s/%d.backup", backupDir, time.Now().Unix())

	path, err := postgres.DumpDatabase(postgresOptions, filePath)

	return BackupResult{FilePath: path, Err: err}
}
