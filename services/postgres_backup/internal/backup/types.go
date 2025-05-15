package backup

import "time"

type BackupExecutor struct {
	timer *time.Timer
}

type BackupResult struct {
	FilePath string
	Err      error
}
