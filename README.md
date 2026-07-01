# Обозреватель Технической Документации

Официальное название проекта: Обозреватель Технической Документации.

Платформа для работы с технической документацией EPC/5GC и телеком-оборудованием, вдохновленная Huawei HedEx и дополненная современным пользовательским интерфейсом и возможностями искусственного интеллекта.

В репозитории подготовлен стартовый минимально жизнеспособный каркас на базе:

- Python + FastAPI (серверная часть API)
- OpenSearch (полнотекстовый поиск и фасетная фильтрация)
- Слой искусственного интеллекта (контракт, готовый к подключению RAG)

## CLI Quick Reference

Все CLI-команды (запускать из папки `backend`):

| Категория | Команда | Назначение |
| --- | --- | --- |
| Справка | `python -m app.cli --help` | Общая справка по CLI и списку групп команд. |
| Справка | `python -m app.cli users --help` | Справка по группе `users` и списку подкоманд. |
| Справка | `python -m app.cli users list --help` | Справка по команде `users list`. |
| Справка | `python -m app.cli users add --help` | Справка по команде `users add` и ее параметрам. |
| Справка | `python -m app.cli users update --help` | Справка по команде `users update` и ее параметрам. |
| Справка | `python -m app.cli users delete --help` | Справка по команде `users delete` и ее параметрам. |
| Gate | `python scripts/phase0_gate.py` | Автоматическая gate-проверка Фазы 0 (PASS/FAIL одним запуском). |
| Gate | `python scripts/phase1_seed_docs.py --count 300` | Подготовка данных для проверки критерия Фазы 1 по количеству документов. |
| Gate | `python scripts/phase1_gate.py --offline-search --min-docs 300 --search-runs 30 --p95-ms 300` | Автоматическая gate-проверка критериев выхода Фазы 1. |
| Пользователи | `python -m app.cli users list` | Печатает таблицу зарегистрированных пользователей: логин, имя, контакты, `failed`, `total_failed_attempts`, блокировка, `created_at` (MSK `+03:00`). |
| Пользователи | `python -m app.cli users add --login engineer --password StrongPass1 --email engineer@example.com --display-name "Инженер"` | Добавляет нового пользователя. |
| Пользователи | `python -m app.cli users update --login engineer --display-name "Старший инженер" --password NewStrongPass1` | Обновляет имя и пароль пользователя. |
| Пользователи | `python -m app.cli users update --login engineer --phone +79001112233 --clear-email` | Переключает канал контакта на телефон и очищает email. |
| Пользователи | `python -m app.cli users update --login engineer --unlock` | Сбрасывает блокировку и счетчик неудачных входов (`failed`). |
| Пользователи | `python -m app.cli users delete --login engineer` | Удаляет пользователя. |

## Проверка Фазы 0

Минимальный gate-чек можно запускать одной командой:

```powershell
python scripts/phase0_gate.py
```

Ожидаемый результат: `PHASE0_GATE=PASS` и код выхода `0`.

Ручная проверка (4 команды и ожидаемые коды):

| Проверка | Команда | Ожидаемый код |
| --- | --- | --- |
| Health | `Invoke-WebRequest http://localhost:8000/health` | `200` |
| OpenAPI | `Invoke-WebRequest http://localhost:8000/openapi.json` | `200` |
| Search API | `Invoke-WebRequest http://localhost:8000/api/v1/search -Method POST -ContentType "application/json" -Body '{"query":"paging","page":1,"size":10,"filters":{}}'` | `200` |
| AI API | `Invoke-WebRequest http://localhost:8000/api/v1/ai/ask -Method POST -ContentType "application/json" -Body '{"question":"Что такое AMF?","context_doc_ids":[],"max_citations":3}'` | `200` |

## Проверка Фазы 1

Быстрый порядок проверки критериев выхода:

```powershell
python scripts/phase1_seed_docs.py --count 300
python scripts/phase1_gate.py --offline-search --min-docs 300 --search-runs 30 --p95-ms 300
```

Ожидаемый итог: `PHASE1_GATE=PASS` и код выхода `0`.

## Цели

- Получить рабочий прототип за недели, а не за месяцы
- Поддержать документацию Open5GS, Ericsson, Huawei и других вендоров
- Сначала сохранять архитектуру простой, а узкие места оптимизировать по метрикам (Go/C++)

## Целевой вид продукта

Интерфейс строится по принципам HedEx:

- Левая панель: дерево документации (продукт/версия/домен/тема)
- Верхняя панель: глобальный поиск и переключение версии
- Центральная область: режим чтения статьи
- Правая панель: ассистент искусственного интеллекта с ответами только на основе источников

## Структура репозитория

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   ├── opensearch_client.py
│   │   │   └── search_service.py
│   │   ├── static/
│   │   │   ├── app.js
│   │   │   ├── glossary.json
│   │   │   ├── index.html
│   │   │   └── styles.css
│   │   ├── config.py
│   │   ├── main.py
│   │   └── schemas.py
│   ├── tests/
│   │   ├── test_glossary_api.py
│   │   └── test_phase1_smoke.py
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/app/
│   ├── package.json
│   └── .env.local.example
├── docker-compose.yml
└── ROADMAP.md
```

## Быстрый старт

Ниже приведена рекомендуемая последовательность для локальной работы в Windows PowerShell.

### 1. Запуск OpenSearch

```powershell
docker compose up -d opensearch
```

Опционально можно запустить дашборд:

```powershell
docker compose up -d opensearch-dashboards
```

### 2. Создание виртуального окружения

```powershell
cd backend
py -m venv .venv
```

### 3. Активация виртуального окружения и установка зависимостей

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Настройка переменных окружения

```powershell
Copy-Item .env.example .env
```

Значения по умолчанию подходят для локального OpenSearch в Docker.

### 5. Запуск серверной части API

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Запуск тестов

```powershell
python -m pytest -q
```

### 7. Запуск клиентского приложения Next.js + TypeScript

В отдельном терминале:

```powershell
cd ..\frontend
Copy-Item .env.local.example .env.local
npm install
npm run dev
```

Клиент будет доступен по адресу: <http://localhost:3000>

Клиент использует встроенные Next.js proxy маршруты для backend API:

- `GET /api/documents/tree` -> `GET /api/v1/documents/tree`
- `GET /api/documents/{docId}` -> `GET /api/v1/documents/{doc_id}`

Основные UI-возможности Фазы 2:

- левая древовидная навигация по продуктам, релизам, доменам и темам;
- breadcrumb для текущего документа;
- переключение версии релиза;
- базовая страница чтения документа с якорями по разделам.
- сохраненные поиски по дереву документации (localStorage);
- закрепленные разделы (якоря) для открытого документа (localStorage);
- адаптивный макет для desktop/mobile.
- интерактивная строка поиска с мгновенными подсказками по загруженным документам;
- фильтры библиотеки по типу, релизу и продуктовой папке;
- вкладка `Справочник` с поиском по терминам и аббревиатурам;
- отдельная вкладка `Администрирование` для управления справочником (только для роли `admin`);
- переключение языка отображения справочника (RU/EN) и сортировка по аббревиатуре/названию;
- переход из карточки термина в связанные и закрепленные документы библиотеки.

### 8. Проверка документации API

- Swagger UI: <http://localhost:8000/docs>
- Проверка состояния сервиса: <http://localhost:8000/health>
- Стартовый интерфейс дерева и чтения: <http://localhost:8000/>

## Справочник

Вкладка `Справочник` предназначена для работы с терминами и аббревиатурами EPC/5GC.

Текущие возможности:

- поиск по аббревиатуре, русскому и английскому названию;
- переключение языка отображения описаний (`RU` / `EN`);
- сортировка по аббревиатуре, русскому или английскому названию;
- блок `Закрепленные источники` для ручных ссылок на документы;
- блок `Связанные документы`, который автоматически подбирает релевантные загруженные документы по ключевым словам термина;
- переход из карточки термина прямо в документ библиотеки.

Источник данных справочника:

- основное рабочее хранилище — SQLite в `STORAGE_DB_PATH`;
- `backend/app/static/glossary.json` используется как начальный seed при пустой базе и как удобный переносимый шаблон.

API справочника:

- `GET /api/v1/glossary` — публичное чтение всех записей справочника;
- `POST /api/v1/glossary` — создание записи, только `admin`;
- `PATCH /api/v1/glossary/{abbr}` — обновление записи, только `admin`;
- `DELETE /api/v1/glossary/{abbr}` — удаление записи, только `admin`;
- `GET /api/v1/glossary/export` — экспорт справочника в JSON, только `admin`;
- `POST /api/v1/glossary/import` — импорт JSON в справочник, только `admin`.

Структура записи glossary:

```json
{
  "abbr": "AMF",
  "term_ru": "Функция управления доступом и мобильностью",
  "term_en": "Access and Mobility Management Function",
  "definition_ru": "Описание на русском языке.",
  "definition_en": "Description in English.",
  "related": ["SMF", "AUSF", "gNB"],
  "keywords": ["amf", "mobility"],
  "manual_sources": [
    {
      "label": "Ericsson EPC Mobility Management Guide",
      "doc_title_match": "Ericsson EPC Mobility Management Guide"
    }
  ]
}
```

Поддерживаемые поля `manual_sources`:

- `label` — отображаемое имя ссылки в карточке термина;
- `doc_title_match` — подстрока для поиска документа среди уже загруженных;
- `doc_id` — прямой идентификатор документа, если он известен.

Административный режим справочника:

- появляется как отдельная вкладка `Администрирование` после входа под пользователем с ролью `admin`;
- поддерживает фильтр записей, пагинацию, создание/редактирование/удаление;
- поддерживает экспорт и импорт glossary в JSON;
- для `manual_sources` используется отдельный визуальный редактор строк источников вместо ручного текстового формата.

Примечание:

- Для запуска тестов используйте `python -m pytest`, а не просто `pytest`.
- Если какая-либо зависимость не устанавливается под Python 3.14, рекомендуется использовать Python 3.12 или 3.13.
- Для `fastapi.testclient` требуется пакет `httpx` (уже добавлен в `requirements.txt`).

## Проверенный стек для Python 3.14

Ниже перечислены версии, которые проверены в этом проекте на Windows + Python 3.14:

- fastapi==0.136.3
- starlette==0.52.1
- pydantic>=2.13.4,<3
- pydantic-settings>=2.14.1,<3
- httpx==0.28.1

Проверка на этом стеке:

- `python -m pip install -r requirements.txt` — успешно.
- `python -m pytest -q` — успешно (`10 passed`).

## Маршруты API (минимально жизнеспособная версия)

- GET /health - состояние сервиса
- POST /api/v1/search - полнотекстовый поиск и фасетная фильтрация
- GET /api/v1/metrics/kpi - KPI метрики (количество документов, p95 задержки поиска, число замеров)
- GET /api/v1/metrics/panels - панели мониторинга (ошибки, задержки, пропускная способность)
- GET /api/v1/metrics/hotspots - список узких мест по стадиям (avg/p95)
- GET /api/v1/documents/tree - дерево документации (продукт/версия/домен/тема)
- GET /api/v1/documents/{doc_id} - чтение документа и его чанков
- POST /api/v1/documents/upload - загрузка и индексация документа (поддерживает `X-Idempotency-Key`)
- POST /api/v1/documents/package-gotd - упаковка библиотеки `.gotd` из стандартных файлов
- POST /api/v1/ai/ask - контракт ответа искусственного интеллекта с привязкой к источникам
- POST /api/v1/ai/feedback - пользовательская оценка ответа AI (`like`/`dislike`) с привязкой к `trace_id`
- POST /api/v1/auth/login/password - вход по логину и паролю
- POST /api/v1/auth/sms/send-code - отправка СМС-кода подтверждения
- POST /api/v1/auth/sms/verify - подтверждение СМС-кода
- POST /api/v1/auth/qr/create - создание QR-сессии входа
- GET /api/v1/auth/qr/status/{session_id} - проверка статуса QR-сессии
- POST /api/v1/auth/qr/confirm - подтверждение QR-сессии (демо-режим)
- POST /api/v1/auth/register/validate - валидация данных регистрации
- POST /api/v1/auth/register/start - старт регистрации и отправка кода подтверждения
- POST /api/v1/auth/register/confirm - подтверждение кода и создание пользователя
- GET /api/v1/admin/users - список пользователей, только для роли `admin` по Bearer-токену
- POST /api/v1/admin/users - создание пользователя, только для роли `admin`
- PATCH /api/v1/admin/users/{login} - обновление пользователя, только для роли `admin`
- DELETE /api/v1/admin/users/{login} - удаление пользователя, только для роли `admin`
- GET /api/v1/admin/audit - журнал административных действий, только для роли `admin`
- GET /api/v1/admin/audit/ai - журнал ответов AI, только для роли `admin`

### Фаза 4: легкая ролевая модель и аудит

- Все успешные входы теперь возвращают `role` вместе с `access_token`.
- Роль `admin` по умолчанию назначена учетной записи `admin`.
- Административные операции требуют заголовок `Authorization: Bearer <token>` и проверяют роль `admin`.
- Создание, обновление и удаление пользователей пишутся в `admin_audit_log`.
- Каждый ответ AI пишет аудит-событие в `ai_answer_audit_log`.
- Загрузка документов поддерживает идемпотентность через `X-Idempotency-Key`.
- Индексация при загрузке выполняется с повторными попытками при временных сбоях OpenSearch.
- Добавлена метрика-панель `GET /api/v1/metrics/panels`.

### Операционная инструкция (backup/restore)

- Документ runbook: `OPERATIONS_BACKUP_RESTORE.md`.

### Фаза 5: оптимизация производительности

- Поиск использует гибридное ранжирование с повторным rerank по coverage/metadata признакам.
- Метрики узких мест доступны через `GET /api/v1/metrics/hotspots`.
- Автоматизированный gate-чек для этапа оптимизации: `python scripts/phase5_gate.py`.
- Решение по миграции upload-воркеров на Go и CPU-парсинга на C++ принимается по порогам p95 в `phase5_gate.py`.

Пример ответа для `GET /api/v1/metrics/kpi`:

```json
{
  "indexed_documents_total": 0,
  "search_latency_p95_ms": 0.0,
  "search_samples": 0
}
```

### Smoke и CI

- В тестовый набор добавлен отдельный smoke-тест для `GET /api/v1/metrics/kpi`.
- Для glossary API добавлен отдельный тестовый файл: `backend/tests/test_glossary_api.py`.
- Актуальный статус локального прогона: `python -m pytest -q` -> `10 passed`.

### Завершение сеанса

- Выход из программы доступен через кнопку с именем пользователя в правом верхнем углу и пункт меню `Выход из программы`.
- Если пользователь не проявляет активность в течение 30 минут, сеанс автоматически завершается и требуется повторный вход.

### Демо-данные для входа

- Логин: `admin`
- Пароль: `admin123`

## Поддержка формата .gotd

Поддерживаются два сценария:

- Упаковка библиотеки `.gotd` из стандартных файлов (`txt`, `csv`, `doc`, `docx`, `html`, `pdf` и других).
- Загрузка и чтение библиотеки `.gotd` с распаковкой и индексацией вложенных документов.

Рекомендуемый поток:

1. Вызвать `POST /api/v1/documents/package-gotd` и передать исходные файлы.
2. Полученный архив `.gotd` загрузить через `POST /api/v1/documents/upload`.
3. Проверить дерево документов через `GET /api/v1/documents/tree`.

## Хранение данных

- Полнотекстовый поиск и фасеты обслуживаются через OpenSearch.
- Постоянный реестр документов и чанков хранится в SQLite.
- Путь к SQLite можно переопределить через переменную окружения `STORAGE_DB_PATH`.

## Модель метаданных поиска (текущее состояние)

Каждый индексируемый фрагмент (чанк) должен содержать телеком-метаданные:

- product (название продукта или линейки)
- vendor (ericsson, huawei, open5gs и т.д.)
- domain (epc, 5gc, ims, ran)
- release (R15/R16/R17/vendor release)
- node_type (AMF/SMF/UPF/MME/SGW/PGW...)
- interface (N1/N2/N4/S1-MME/S5...)
- protocol (PFCP/GTP-C/GTP-U/Diameter/SCTP...)

## Примечания по искусственному интеллекту

Текущий модуль искусственного интеллекта реализует базовый retrieval-конвейер:

- извлекает релевантные чанки из OpenSearch по вопросу;
- учитывает ограничение `context_doc_ids` (если передано);
- возвращает реальные `citation`/`snippet` из индексированных источников;
- формирует source-grounded ответ без генерации утверждений вне найденного контекста.

## Smoke Protocol: Регрессионный чек-лист

Формальный регрессионный сценарий для проверки функциональности администратора справочника и журнала аудита:

**Автоматизированная проверка (pytest):**

```powershell
python -m pytest tests/test_glossary_api.py::test_glossary_admin_e2e_crud_with_audit_and_export -v
```

Тест проверяет сквозной сценарий:
1. Вход администратора (логин `admin`, пароль `admin123`).
2. Создание новой записи справочника (аббревиатура, русское и английское названия, описания, связанные термины, ключевые слова).
3. Проверка появления записи в публичном справочнике (`GET /api/v1/glossary`).
4. Обновление (PATCH) записи справочника с проверкой изменений.
5. Проверка аудит-журнала (`GET /api/v1/admin/audit`) на наличие `admin.glossary.create` и `admin.glossary.update` событий.
6. Экспорт справочника (JSON) и проверка наличия записи в экспортированных данных.
7. Удаление (DELETE) записи справочника.
8. Проверка удаления из публичного справочника.
9. Проверка аудит-журнала на наличие `admin.glossary.delete` события.

**Ручная проверка (UI-флоу):**

Запустить сервер:
```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Открыть браузер: `http://localhost:8000/#glossary-admin`

Шаги:
1. Нажать на кнопку профиля, убедиться, что текущая роль = `Администратор`.
2. Нажать кнопку **Новая запись**, заполнить форму:
   - Аббревиатура: `TEST01`
   - Русское название: `Тестовый термин`
   - English name: `Test term`
   - Описание RU: `Тестовое описание`
   - Description EN: `Test description`
   - Ключевые слова: `test, regression`
   - Связанные термины: `AMF, SMF`
3. Нажать **Сохранить** и подтвердить сообщение «Запись TEST01 сохранена».
4. Отредактировать русское название на `Тестовый термин (обновлен)`.
5. Нажать **Сохранить** и подтвердить обновление.
6. Нажать **Обновить** в разделе «Журнал изменений справочника» и убедиться:
   - Есть `admin.glossary.create` событие для TEST01
   - Есть `admin.glossary.update` событие для TEST01
7. Нажать **Шаблон JSON** и убедиться в сообщении «Шаблон glossary-template.json скачан».
8. Нажать **Удалить** и подтвердить удаление (сообщение «Запись TEST01 удалена»).
9. Нажать **Обновить** в журнале и убедиться в наличии `admin.glossary.delete` события для TEST01.

**Регрессионный чек-лист (быстрая проверка):**

| Компонент | Проверка | Статус |
| --- | --- | --- |
| Публичный читатель | GET /api/v1/glossary возвращает список терминов | ✅ |
| Admin CRUD | POST /api/v1/glossary (создание) с auth | ✅ |
| Admin CRUD | PATCH /api/v1/glossary/{abbr} (обновление) с auth | ✅ |
| Admin CRUD | DELETE /api/v1/glossary/{abbr} (удаление) с auth | ✅ |
| Admin экспорт | GET /api/v1/glossary/export возвращает JSON с entries | ✅ |
| Admin импорт | POST /api/v1/glossary/import импортирует JSON | ✅ |
| Аудит | GET /api/v1/admin/audit показывает action, target, actor, status | ✅ |
| Ролевой контроль | 401 для анонимных CRUD-операций | ✅ |
| Ролевой контроль | 403 для user-роли на DELETE | ✅ |
| UI админ | Админ-вкладка видна для пользователя с ролью admin | ✅ |
| UI админ | Кнопка загрузки шаблона (Шаблон JSON) | ✅ |
| UI админ | Журнал изменений показывает события и фильтруется по target | ✅ |
| UI админ | Создание/обновление/удаление работают в админ-интерфейсе | ✅ |

Поддерживаемые режимы `POST /api/v1/ai/ask`:

- `mode: "explain"` — объяснение по найденному контексту;
- `mode: "compare"` — сравнение по найденным источникам;
- `mode: "diagnose"` — диагностический шаблон по найденным чанкам.

Строгая политика источников:

- `source_policy: "strict-required-citations"`;
- если цитаты не найдены, ответ возвращается в режиме `blocked=true`;
- для трассировки возвращаются `trace_id` и `retrieval_stats`.

Цикл обратной связи:

- `POST /api/v1/ai/feedback` принимает `trace_id`, `vote` (`like`/`dislike`) и опциональный `reason`;
- оценки сохраняются в SQLite и могут использоваться для последующей калибровки качества ответов.

Следующий шаг Фазы 3: подключение полноценной LLM/RAG-генерации поверх retrieval-слоя.

Критичные требования к модулю искусственного интеллекта для промышленного контура:

- Ответы должны содержать ссылки на источники
- Нельзя возвращать утверждения без подтвержденных источников
- Должны быть указаны уровень уверенности и ссылки на документы

## Следующие шаги

План по этапам смотрите в [ROADMAP.md](ROADMAP.md).

## Эквиваленты терминов (английский -> русский)

Правило обновления: каждый новый термин добавляется в этот список автоматически и в алфавитном порядке по английскому термину.

Формат записи для новых терминов:

- `English term -> русский эквивалент`

Дополнительное правило: английская часть термина пишется с заглавной буквы.

- AI -> искусственный интеллект
- AI assistant -> ассистент искусственного интеллекта
- API contract -> контракт API
- API endpoint -> маршрут API
- Audit log -> журнал аудита
- Backend -> серверная часть
- Baseline -> базовый порог
- Chunk -> чанк (фрагмент)
- Citation -> ссылка на источник
- Confidence score -> уровень уверенности
- Document ingestion -> загрузка документов
- Faceted filtering -> фасетная фильтрация
- Faceted search -> фасетный поиск
- Filter -> фильтр
- Frontend -> клиентская часть
- Full-text search -> полнотекстовый поиск
- Golden queries -> эталонные запросы
- Grounded answer -> ответ с привязкой к источникам
- Health check -> проверка состояния сервиса
- Highlight -> подсветка фрагментов
- Index mapping -> схема индекса
- Ingestion pipeline -> конвейер загрузки документов
- Latency -> задержка
- Metadata -> метаданные
- MVP (Minimum Viable Product) -> минимально жизнеспособная версия
- Retrieval -> извлечение контекста
- Retrieval pipeline -> конвейер извлечения контекста
- Reranking -> повторное ранжирование
- Roadmap -> дорожная карта
- Runbook -> операционная инструкция
- Search -> поиск
- Source citation -> ссылка на источник
- Source-grounded answer -> ответ с привязкой к источникам
- Throughput -> пропускная способность
- UX (User Experience) -> пользовательский опыт
