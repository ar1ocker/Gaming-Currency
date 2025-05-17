package application

import (
	"fmt"
	"strings"
	"time"

	"postgres_backup/internal/postgres"

	"github.com/knadh/koanf/v2"
)

type Config struct {
	postgres postgres.PostgresOptions

	backupInterval time.Duration
	backupDir      string
	backupChatIDs  []string

	admins []string
}

func (c *Config) LoadFromKoanf(k *koanf.Koanf) (*Config, error) {
	requiredPaths := []string{"admins", "backup.dir", "backup.interval", "backup.chatIDs", "postgres.dbName", "postgres.host", "postgres.password", "postgres.user", "postgres.port"}

	notExists := make([]string, 0, len(requiredPaths))

	for _, path := range requiredPaths {
		if !k.Exists(path) {
			notExists = append(notExists, path)
		}
	}

	if len(notExists) > 0 {
		return c, fmt.Errorf("Not found params in config: %v", strings.Join(notExists, ", "))
	}

	interval, err := time.ParseDuration(k.String("backup.interval"))
	if err != nil {
		return c, fmt.Errorf("Parsing error in backupInterval value: %v", err)
	}

	c.admins = k.Strings("admins")
	c.backupDir = k.String("backup.dir")
	c.backupInterval = interval
	c.backupChatIDs = k.Strings("backup.chatIDs")
	c.postgres.DBName = k.String("postgres.dbName")
	c.postgres.Host = k.String("postgres.host")
	c.postgres.Password = k.String("postgres.password")
	c.postgres.Port = k.String("postgres.port")
	c.postgres.User = k.String("postgres.user")

	return c, nil
}
