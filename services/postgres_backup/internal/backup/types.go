package backup

import (
	"sync"
	"time"
)

type BackupExecutor struct {
	NextRunTime time.Time

	timer *time.Timer
	mu    sync.Mutex
}

type BackupResult struct {
	FilePath string
	Err      error
}
