# 🌿 Smart Garden Bot

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/backend-GitHub%20Actions-black.svg)](https://github.com/features/actions)

Telegram-бот для домашнего сада. Напоминает о поливе и подкормках, учитывает погоду и сохраняет историю напоминаний. Может работать через GitHub Actions, без отдельного сервера.

---

## ✨ Возможности

- 💧 **Напоминания о поливе** — бот проверяет интервал `waterFreq` для каждого растения.
- 🧪 **Напоминания о подкормках** — поддерживаются разные схемы по сезонам, стадиям роста и условиям.
- 🌡 **Учёт погоды** — используются данные OpenWeatherMap: температура, влажность, ветер.
- 🧠 **Память** — бот хранит историю последних напоминаний в JSON-файлах.
- 📅 **Гибкая настройка** — у каждого растения можно задать собственные параметры ухода.
- 🚀 **Автозапуск** — проект подходит для запуска по расписанию через GitHub Actions.

---

## 📂 Структура

| Файл | Описание |
| :--- | :--- |
| `send_tasks.py` | Основной скрипт: проверка расписания, погоды, формирование сообщения, отправка в Telegram |
| `plants.json` | База растений: частота полива, стадия, условия и схемы подкормок |
| `history.json` | История напоминаний о поливе |
| `feed_history.json` | История напоминаний о подкормках |
| `last_weather.json` | Кэш последней температуры |

---

## ⚙️ Как это работает

1. Скрипт загружает список растений из `plants.json`.
2. Проверяет, прошло ли достаточно дней с последнего напоминания.
3. Получает текущую погоду из OpenWeatherMap.
4. Формирует текст отчёта для Telegram.
5. После успешной отправки обновляет `history.json`, `feed_history.json` и `last_weather.json`.

---

## 🚀 Быстрый старт

### 1. Форк репозитория

Нажмите **Fork** в правом верхнем углу.

### 2. Добавьте секреты

Перейдите в **Settings → Secrets and variables → Actions → New repository secret** и добавьте значения:

| Секрет | Описание |
| :--- | :--- |
| `TELEGRAM_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_CHAT_ID` | Ваш Chat ID |
| `OPENWEATHER_API_KEY` | Ключ OpenWeatherMap |
| `CITY_NAME` | Название города, например `Moscow` |

### 3. Дайте права на запись

Перейдите в **Settings → Actions → General → Workflow permissions**. Выберите **Read and write permissions** и нажмите **Save**. Это нужно, чтобы бот мог обновлять JSON-файлы с историей.

### 4. Настройте растения

Пример структуры `plants.json`:

```json
{
  "plants": [
    {
      "id": "lemon-tree",
      "name": "Лимон",
      "waterFreq": 4,
      "stage": "foliage",
      "flags": {
        "active_growth": true
      },
      "feeds": [
        {
          "id": "succinic",
          "name": "Янтарка",
          "dose": "1/2 дозы",
          "intervalDays": 30,
          "months": [3, 4, 5, 6, 7, 8],
          "onlyStages": ["foliage"]
        }
      ]
    }
  ]
}
```

---

## ▶️ Запуск локально

```bash
python send_tasks.py
```

Перед запуском убедитесь, что установлены зависимости и заданы переменные окружения.

---

## 📝 Формат данных

### `history.json`
Хранит дату последнего напоминания о поливе:

```json
{
  "lemon-tree": {
    "last_reminded": "2026-03-30T07:15:00+00:00"
  }
}
```

### `feed_history.json`
Хранит дату последнего напоминания о подкормке:

```json
{
  "lemon-tree": {
    "succinic": {
      "last_done": "2026-03-20T08:00:00+00:00"
    }
  }
}
```

---

## 🔧 Зависимости

Минимум нужен Python 3.12+ и библиотека `requests`.

Установка:

```bash
pip install requests
```

---

## 📌 Примечание

Сейчас проект использует локальную логику правил и погодные данные. В текущей версии интеграции с Google Gemini в коде нет.
