package backup

import (
	"context"
	"fmt"
	"log"
	"time"

	"postgres_backup/internal/postgres"
)

func NewBackupExecutor() *BackupExecutor {
	timer := time.NewTimer(0)

	if !timer.Stop() {
		<-timer.C
	}

	return &BackupExecutor{timer: timer}
}

func (executor *BackupExecutor) RunBackupAfter(duration time.Duration) (alreadyRunned bool) {
	executor.mu.Lock()
	defer executor.mu.Unlock()

	return !executor.timer.Reset(duration)
}

func (executor *BackupExecutor) CreatePeriodicBackupChan(ctx context.Context, interval time.Duration, postgresOptions postgres.PostgresOptions, backupDir string) <-chan BackupResult {
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

				select {
				case <-ctx.Done():
					return
				case resultChan <- result:
					elapsed := time.Since(startTime)
					if elapsed > interval {
						log.Printf("backup took too long: %v (interval is %v)", elapsed, interval)
					}

					nextInterval := max(interval-elapsed, 0)
					executor.RunBackupAfter(nextInterval)
				}
			}
		}
	}()

	return resultChan
}

func (executor *BackupExecutor) DumpDatabase(postgresOptions postgres.PostgresOptions, backupDir string) BackupResult {
	filePath := fmt.Sprintf("%s/%d.backup", backupDir, time.Now().Unix())

	path, err := postgres.DumpDatabase(postgresOptions, filePath)

	return BackupResult{FilePath: path, Err: err}
}
