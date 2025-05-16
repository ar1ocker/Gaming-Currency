package backup

import (
	"sync"
	"time"
)

type BackupExecutor struct {
	timer *time.Timer
	mu    sync.Mutex
}

type BackupResult struct {
	FilePath string
	Err      error
}
