# 1. Базовый минимальный образ Python 3.12
FROM python:3.12-slim

# 2. Рабочая директория внутри контейнера
WORKDIR /app

# 3. Копируем список библиотек и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Копируем весь исходный код (main.py и т.д.)
COPY . .

# 5. Запуск FastAPI через Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
