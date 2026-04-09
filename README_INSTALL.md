# Reciper - Установка и использование

## 🚀 Быстрая установка (одной командой)

### Вариант 1: Через pip (рекомендуется)
```bash
pip install reciper
```

### Вариант 2: Через pipx (изолированная установка)
```bash
pipx install reciper
```

### Вариант 3: Из исходников
```bash
git clone https://github.com/yourusername/reciper.git
cd reciper
pip install -e .
```

## 📋 Использование

### Базовый анализ пайплайна
```bash
# Перейдите в папку с вашим пайплайном
cd /path/to/your/pipeline

# Запустите анализ одной командой
reciper analyze .
```

### Полный анализ с проверкой
```bash
reciper analyze . --verbose
```

### Что делает команда:
1. **Сканирует** все Python файлы в директории
2. **Извлекает** импорты пакетов (numpy, pandas, biopython и др.)
3. **Обнаруживает** вызовы внешних утилит через subprocess (samtools, bwa, fastqc, etc.)
4. **Генерирует**:
   - `environment.yml` - Conda окружение
   - `Dockerfile` - Docker образ со всеми зависимостями
   - Lock файлы для воспроизводимости (если установлены conda-lock/pip-tools)
5. **Проверяет** корректность сгенерированных файлов
6. **Детектирует** конфликты версий между пакетами

## 📁 Результат работы

После запуска вы получите:

```
your_pipeline/
├── environment.yml      # Conda окружение
├── Dockerfile          # Docker образ
└── ... ваши файлы ...
```

### Пример Dockerfile для биоинформатики:
```dockerfile
FROM continuumio/miniconda3:latest

WORKDIR /app

# Системные пакеты (обнаруженные автоматически)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    samtools bcftools fastqc multiqc bwa && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Python пакеты
COPY environment.yml .
RUN conda env update -f environment.yml

CMD ["/bin/bash"]
```

## 🔧 Опции команды

| Опция | Описание |
|-------|----------|
| `-o, --output` | Директория для выходных файлов (по умолчанию: текущая) |
| `-v, --verbose` | Подробный вывод с отладочной информацией |
| `--no-verify` | Пропустить проверку сгенерированных файлов |
| `--no-lock` | Не генерировать lock файлы |
| `--no-conflict-check` | Отключить проверку конфликтов версий |
| `--json` | Вывести JSON отчет в stdout |
| `--report-file` | Сохранить JSON отчет в файл |

## 💡 Примеры использования

### Анализ простого проекта
```bash
cd my_bioinformatics_project
reciper analyze .
```

### Анализ с подробным выводом
```bash
reciper analyze /path/to/pipeline --verbose
```

### Анализ с сохранением отчета
```bash
reciper analyze . --report-file analysis_report.json
```

### Анализ без проверки (быстрее)
```bash
reciper analyze . --no-verify
```

## 🎯 Для кого этот инструмент?

- **Биоинформатики**, публикующие пайплайны в статьях
- **Лаборатории**, стандартизирующие окружения
- **Разработчики NGS workflows**
- **Исследователи**, желающие обеспечить воспроизводимость

## ✅ Гарантии

Сгенерированный Dockerfile:
- ✅ Содержит все необходимые Python пакеты
- ✅ Включает системные утилиты (samtools, bwa, etc.) обнаруженные через анализ subprocess
- ✅ Проходит проверку синтаксиса
- ✅ Готов к сборке и использованию

## 🔗 Следующие шаги

После генерации файлов:

```bash
# Сборка Docker образа
docker build -t my_pipeline .

# Запуск контейнера
docker run -it my_pipeline

# Или создание conda окружения
conda env create -f environment.yml
conda activate generated-environment
```
