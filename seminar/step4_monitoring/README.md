# Шаг 4: Мониторинг FastAPI сервиса - Домашнее задание

Система мониторинга для FastAPI сервиса инференса ONNX (из шага 2). Поддерживает:
- Метрики: Response Time, P95 Latency, Error Rate, Health Status, Consecutive Failures
- Цветные алерты (зелёный/жёлтый/красный) с настраиваемыми порогами и cooldown
- Структурированное логирование в JSON + цветной консольный вывод
- Тестирование `/predict` с отправкой случайного изображения (PNG) — без внешних зависимостей данных

## Архитектура

```
step4_monitoring/
├── main.py
├── src/
│   ├── monitor.py
│   ├── logger.py
│   └── config.py
├── config/
│   └── monitoring_config.yaml
├── logs/
└── README.md
```

## Установка

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install pyyaml requests pillow numpy
```

> Pillow и NumPy используются для генерации случайного PNG. Если они недоступны, монитор всё равно работает, но /predict-запросы могут завершиться ошибкой — это ожидаемо, и метрики/алерты отразят проблему.

## Конфигурация

Конфиг: `config/monitoring_config.yaml`

- `service.base_url` — адрес сервиса FastAPI.
- `monitoring.check_interval_seconds` — периодичность проверок.
- `monitoring.samples_per_check` — число POST /predict за один цикл.
- `thresholds.*` — warning/critical пороги.
- `alerts.enabled`, `alerts.cooldown_minutes` — алерты и окно подавления.
- `logging.*` — пути логов и включение цвета для консоли.

Можно переопределить путь к конфигу через переменную окружения `MONITORING_CONFIG` или аргумент `--config`.

## Запуск

```bash
python main.py --once  # единичная проверка
python main.py         # постоянный мониторинг
```

## Как это работает

1. `/health` — проверка доступности (HTTP 200 ⇒ OK).
2. `/predict` — несколько запросов с изображением, измеряется время ответа и статус.
3. Агрегация метрик: p95, error rate, последовательные неудачи.
4. Выбор цвета статуса по наихудшему из метрик.
5. Алерты в консоль и JSON-лог с учетом cooldown.
6. Метрики пишутся в JSONL `logs/metrics.jsonl` (по одной строке на цикл).

## Формат логов

- **`logs/monitoring.log`** — JSON-строки с полями `ts`, `level`, `name`, `msg`, плюс контекст (`health`, `predict`, `alert_color` и т.п.).
- **`logs/metrics.jsonl`** — по строке на цикл:
  ```json
  {"ts":"2025-10-06T12:00:00Z","response_times_ms":[123.4, 150.2, 200.9],"p95_latency_ms":200.9,"error_rate_percent":0.0,"health_ok":true,"consecutive_failures":0}
  ```

## Примечания по интеграции с сервисом из шага 2

- Эндпоинт `/predict` ожидается в формате `multipart/form-data` с полем файла `file` (имя можно поменять в `monitor.py` при необходимости).
- Если ваш сервис использует иное имя поля или дополнительные поля (например, `threshold`, `top_k`), добавьте их в `data`/`headers` в методе `_predict_once`.
- Эндпоинт `/health` должен возвращать HTTP 200 и JSON/текст.