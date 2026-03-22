# 🌿 Smart Garden Bot

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/backend-GitHub%20Actions-black.svg)](https://github.com/features/actions)

Умный Telegram-бот для домашнего сада. Напоминает о поливе, учитывает погоду и даёт советы от **Google Gemini**. Работает бесплатно через GitHub Actions — сервер не нужен.

---

## ✨ Возможности

- 🧠 **Память** — бот запоминает дату последнего полива и не беспокоит раньше времени
- 🤖 **ИИ-советы** — Google Gemini даёт рекомендации с учётом погоды и сезона
- 🌡 **Погода** — данные с OpenWeatherMap, учёт температуры и влажности
- 📅 **Гибкий график** — индивидуальная частота полива для каждого растения
- 🚀 **Бесплатно** — запускается по cron через GitHub Actions, без VPS и постоянно включённого компьютера

---

## 📂 Структура

| Файл | Описание |
|---|---|
| `send_tasks.py` | Ядро: проверка расписания, погода, запрос к ИИ, отправка в Telegram |
| `plants.json` | База растений: частота полива (`waterFreq`), стадия роста (`stage`) |
| `history.json` | Память бота: даты последних поливов |
| `last_weather.json` | Кэш температуры для отслеживания резких изменений |

---

## 🚀 Быстрый старт

### 1. Форк репозитория

Нажмите **Fork** в правом верхнем углу.

### 2. Добавьте секреты

**Settings → Secrets and variables → Actions → New repository secret**

| Секрет | Описание |
|---|---|
| `TELEGRAM_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_CHAT_ID` | Ваш Chat ID (узнать у @userinfobot) |
| `OPENWEATHER_API_KEY` | Ключ с [openweathermap.org](https://openweathermap.org) |
| `GEMINI_API_KEY` | Ключ с [aistudio.google.com](https://aistudio.google.com) |
| `CITY_NAME` | Название города, например `Moscow` |

### 3. Дайте права на запись

**Settings → Actions → General → Workflow permissions → Read and write permissions → Save**

Это нужно, чтобы бот мог обновлять `history.json` после каждого напоминания.

### 4. Настройте растения

Отредактируйте `plants.json`:

```json
[
  {
    "id": "lemon-tree",
    "name": "Лимон",
    "waterFreq": 4,
    "stage": "active",
    "feedShort": "Цитрусовое удобрение 1/4 дозы"
  }
]
```

Поле `stage` может быть: `active`, `dormant` (покой), `recover` (восстановление).

---

## 📝 Как это работает

1. GitHub Actions запускает `send_tasks.py` по расписанию (cron)
2. Скрипт читает `history.json` и проверяет, пора ли поливать каждое растение
3. Если пора — запрашивает погоду и отправляет запрос в Gemini за советом
4. Отправляет сообщение в Telegram
5. Обновляет `history.json` и делает автоматический `git push`

---

## 🔧 Решение проблем

**Бот каждый раз напоминает об одних растениях**
Проверьте права: Settings → Actions → General → Read and write permissions.
Без права на запись бот не может сохранить дату полива и «забывает» об этом.

**Нет советов от ИИ**
Проверьте, добавлен ли секрет `GEMINI_API_KEY`. Если ключа нет — бот всё равно работает, но без советов.

**Ошибка в логах Actions**
Откройте вкладку Actions → выберите последний запуск → посмотрите вывод шага `Run script`.
