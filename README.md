# sea_battle

Игра "Морской бой" на `Python + Pygame`.

## Требования

- Python `3.12` (рекомендуется)
- На версиях выше `3.12` установка `pygame` может не работать из-за отсутствия готовых wheel

## Установка

```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Запуск

```powershell
python main.py
```

## Управление

- Левая кнопка мыши: выбор кнопок и выстрел по полю противника
- Ввод имени на экране победы: клавиатура

## Структура проекта

- `main.py` — точка входа
- `game/core.py` — состояния игры и основной цикл
- `game/board.py` — поле, корабли, правила попаданий/потопления
- `game/ai.py` — логика ИИ
- `game/ui.py` — UI-константы и кнопки
- `game/scores.py` — чтение/запись рекордов

## Рекорды

- Хранятся локально в `records.json`
- Файл исключен из Git (`.gitignore`)
