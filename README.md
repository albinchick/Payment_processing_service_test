# Payment Processing Service

Асинхронный сервис эмуляции обработки платежей: FastAPI, PostgreSQL, SQLAlchemy Async, RabbitMQ/FastStream, Outbox, webhook и Docker Compose.

## Запуск

Требуются Docker и Docker Compose.

```bash
docker compose up --build
```

API будет доступен на `http://localhost:8000`, Swagger — `http://localhost:8000/docs`, RabbitMQ Management — `http://localhost:15672` (`guest` / `guest`).

По умолчанию API-ключ — `change-me`. Для любого API endpoint используйте заголовок `X-API-Key: change-me`.

## Создать платёж

```bash
curl -X POST http://localhost:8000/api/v1/payments \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me' \
  -H 'Idempotency-Key: order-10001' \
  -d '{
    "amount": "1499.90",
    "currency": "RUB",
    "description": "Оплата заказа",
    "metadata": {"order_id": "10001"},
    "webhook_url": "https://example.com/payment-webhook"
  }'
```

Ожидается `202 Accepted` с `payment_id`, `status` и `created_at`.

## Получить платёж

```bash
curl http://localhost:8000/api/v1/payments/<payment_id> \
  -H 'X-API-Key: change-me'
```

## Миграции

При запуске Compose сервис `migrate` автоматически выполняет `alembic upgrade head`. Локально:

```bash
alembic upgrade head
```

## Тесты

```bash
pytest
```

## Архитектура и допущения

1. API в одной транзакции сохраняет платеж и событие в `outbox`; отдельный publisher публикует событие в RabbitMQ и помечает его опубликованным только после успешной публикации.
2. Обработчик имитирует шлюз случайным исходом: 90% `succeeded`, 10% `failed`, задержка 2–5 секунд.
3. Webhook отправляется с тремя попытками и экспоненциальной задержкой.
4. API и consumer используют один образ Docker, но запускаются разными командами.
5. В тестовом окружении API-ключ задан через переменную окружения; перед реальным развёртыванием замените его на секрет.

## Важное замечание по надёжности

Outbox publisher обеспечивает повторную публикацию при временной ошибке, но при падении процесса между публикацией и записью `published_at` событие может быть опубликовано повторно. Поэтому consumer должен оставаться идемпотентным. Для строгой гарантии exactly-once нужна дополнительная таблица обработанных event ID или иной механизм дедупликации.

Перед production-развёртыванием также стоит отдельно усилить политику retry/DLQ RabbitMQ и интеграционные тесты на брокер и БД.
