# Операционная инструкция: резервное копирование и восстановление

## Область

Документ описывает минимальный runbook для:

- SQLite хранилища приложения (`backend/data/library.db`);
- индекса OpenSearch (`telecom_docs_v1` по умолчанию);
- проверки целостности после восстановления.

## Резервное копирование SQLite

### PowerShell (горячая копия файла)

```powershell
Set-Location backend
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item -Path "data/library.db" -Destination "data/library-$timestamp.db.bak"
```

### Рекомендуемая периодичность

- dev: ежедневно;
- pre-prod/prod: не реже одного раза в час при активной загрузке документов.

## Восстановление SQLite

```powershell
Set-Location backend
Copy-Item -Path "data/library-<timestamp>.db.bak" -Destination "data/library.db" -Force
```

После замены БД перезапустить API-процесс.

## Резервное копирование OpenSearch

### Вариант A: snapshot repository (рекомендуется)

1. Создать snapshot repository (FS или object storage).
2. Выполнить snapshot:

```http
PUT /_snapshot/telecom_repo/snap-<timestamp>?wait_for_completion=true
{
  "indices": "telecom_docs_v1",
  "ignore_unavailable": true,
  "include_global_state": false
}
```

### Вариант B: экспорт через reindex/scroll

Использовать только как fallback при отсутствии snapshot repository.

## Восстановление OpenSearch

```http
POST /_snapshot/telecom_repo/snap-<timestamp>/_restore
{
  "indices": "telecom_docs_v1",
  "include_global_state": false,
  "rename_pattern": "telecom_docs_v1",
  "rename_replacement": "telecom_docs_v1"
}
```

## Проверка после восстановления

1. Проверить health:

```powershell
Invoke-WebRequest http://localhost:8000/health
```

1. Проверить дерево документов:

```powershell
Invoke-WebRequest http://localhost:8000/api/v1/documents/tree
```

1. Выполнить тестовый поиск:

```powershell
Invoke-WebRequest http://localhost:8000/api/v1/search -Method POST -ContentType "application/json" -Body '{"query":"paging","page":1,"size":10,"filters":{}}'
```

1. Проверить панель мониторинга API:

```powershell
Invoke-WebRequest http://localhost:8000/api/v1/metrics/panels
```

## RPO / RTO (базовые ориентиры)

- RPO: до 60 минут;
- RTO: до 30 минут.

## Примечания

- Файл SQLite следует копировать в период минимальной нагрузки.
- Для OpenSearch в production использовать snapshot policy и удаленное хранилище.
- После восстановления рекомендуется выполнить `python -m pytest -q` для smoke-подтверждения.
