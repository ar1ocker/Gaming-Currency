package postgres

import (
	"fmt"
	"os/exec"
)

func DumpDatabase(options PostgresOptions, filePath string) (string, error) {
	cmd := exec.Command("pg_dump", "-h", options.Host, "-p", options.Port, "-U", options.User, "-F", "c", "-b", "-v", "-f", filePath, options.DBName)

	cmd.Env = append(cmd.Env, fmt.Sprintf("PGPASSWORD=%s", options.Password))

	msg, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("ошибка при создание бекапа во время запуска pg_dump %v, %v", err, string(msg))
	}

	return filePath, nil
}
