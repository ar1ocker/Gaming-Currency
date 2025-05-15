package postgres

import (
	"fmt"
	"os/exec"
)

func DumpDatabase(host, port, user, password, dbName, filePath string) (string, error) {
	cmd := exec.Command("pg_dump", "-h", host, "-p", port, "-U", user, "-F", "c", "-b", "-v", "-f", filePath, dbName)

	cmd.Env = append(cmd.Env, fmt.Sprintf("PGPASSWORD=%s", password))

	_, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("Ошибка при создание бекапа во время запуска pg_dump: %v", err)
	}

	return filePath, nil
}
