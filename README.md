# Reciper — One-Command Reproducible Environments for Bioinformatics Pipelines

[![CI](https://github.com/h335h/reciper/actions/workflows/ci.yml/badge.svg)](https://github.com/h335h/reciper/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/reciper.svg)](https://pypi.org/project/reciper/)
[![Python versions](https://img.shields.io/pypi/pyversions/reciper.svg)](https://pypi.org/project/reciper/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Генерация рабочих Docker и conda окружений для биоинформатических пайплайнов одной командой.**

## 🎯 Что это такое?

Reciper — это CLI инструмент, который **автоматически создает гарантированно рабочие окружения** для биоинформатических пайплайнов:

1. **Сканирует** ваш Python код и находит все импорты
2. **Обнаруживает** вызовы внешних утилит (samtools, bwa, fastqc и др.)
3. **Генерирует** `Dockerfile` и `environment.yml` с правильными зависимостями
4. **Проверяет** совместимость пакетов и находит конфликты
5. **Валидирует** окружение через синтаксическую проверку сгенерированных файлов

**Результат:** Ваш коллега сможет запустить пайплайн с первого раза без ошибок "package not found" и конфликтов версий.

---

## ⚡ Быстрый старт

### Установка (одна команда)

```bash
# Вариант 1: Через pip (рекомендуется)
pip install reciper

# Вариант 2: Через pipx (изолированно, не засоряет систему)
pipx install reciper

# Вариант 3: Для разработки
git clone https://github.com/h335h/reciper
cd reciper && pip install -e .
```

### Использование (одна команда)

```bash
# Зайти в папку с пайплайном и запустить анализ
cd /path/to/your/pipeline
reciper analyze .
```

**Это всё!** После выполнения в папке появятся:
- ✅ `Dockerfile` — готовый к сборке контейнер
- ✅ `environment.yml` — conda окружение
- ✅ `environment.lock.yml` — locked версии для воспроизводимости
- ✅ `analysis.json` — подробный отчет (опционально)

---

## 📋 Примеры использования

### Базовый анализ

```bash
# Анализ текущей директории
reciper analyze .

# Анализ с выводом прогресса
reciper analyze . --verbose

# Анализ другой папки
reciper analyze /home/user/ngs_pipeline
```

### Продвинутые опции

```bash
# Сохранить JSON отчет
reciper analyze . --report-file report.json

# Вывести JSON в консоль
reciper analyze . --json

# Пропустить валидацию (быстрее)
reciper analyze . --no-verify

# Отключить проверку конфликтов
reciper analyze . --no-conflict-check

# Указать выходную директорию
reciper analyze . --output ./docker_files
```

### Полный пример для биоинформатического пайплайна

```bash
# 1. Скачиваем пример пайплайна
git clone https://github.com/example/rna-seq-pipeline.git
cd rna-seq-pipeline

# 2. Запускаем Reciper
reciper analyze . --verbose

# 3. Проверяем сгенерированные файлы
cat Dockerfile
cat environment.yml

# 4. Собираем Docker образ (гарантированно рабочий!)
docker build -t rna-seq-pipeline .

# 5. Запускаем контейнер
docker run -it rna-seq-pipeline
```

---

## 🔍 Как это работает?

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Сканирование                                                │
│     ├─ Поиск .py файлов в директории                            │
│     └─ Парсинг AST для извлечения импортов                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Обнаружение зависимостей                                    │
│     ├─ Python пакеты (numpy, pandas, biopython)                 │
│     └─ Системные утилиты (samtools, bwa, fastqc через subprocess)│
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Маппинг на conda/apt                                        │
│     ├─ Python → conda пакеты (biopython, pysam, etc.)           │
│     └─ Команды → apt пакеты (samtools, bowtie2, etc.)           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. Проверка конфликтов                                         │
│     ├─ Анализ совместимости версий                              │
│     └─ Предупреждения о проблемных комбинациях                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. Генерация файлов                                            │
│     ├─ Dockerfile с miniconda3 и apt пакетами                   │
│     ├─ environment.yml для conda                                │
│     └─ environment.lock.yml для воспроизводимости               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  6. Валидация                                                   │
│     ├─ Синтаксическая проверка Dockerfile                       │
│     ├─ Проверка синтаксиса environment.yml                      │
│     └─ (Опционально) Тестовая сборка Docker                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎁 Что вы получаете

### Для разработчика пайплайна:
- ✅ **Автоматизация** — никаких ручных списков зависимостей
- ✅ **Надежность** — обнаружение конфликтов до публикации
- ✅ **Воспроизводимость** — locked версии для точного повторения

### Для пользователя пайплайна:
- ✅ **Запуск с первого раза** — все зависимости указаны правильно
- ✅ **Docker контейнер** — изолированное окружение без конфликтов
- ✅ **Прозрачность** — видно какие пакеты и зачем нужны

---

## 🧬 Поддерживаемые биоинформатические инструменты

### Conda пакеты (автоматический маппинг):
```
biopython, pysam, pybedtools, cyvcf2
pandas, numpy, scipy, scikit-learn
matplotlib, seaborn, plotly
```

### Системные утилиты (обнаружение через subprocess):
```
# Выравнивание
bwa, bowtie2, bowtie, star, hisat2

# Обработка BAM/SAM/VCF
samtools, bcftools, bedtools, vcftools, tabix

# QC и отчеты
fastqc, multiqc, trimmomatic, cutadapt

# BLAST и поиск гомологов
blastn, blastp, blastx, hmmer, muscle, mafft

# Филогенетика
raxml, iqtree, mrbayes

# Аннотация вариантов
snpEff, VEP, annovar
```

Полный список в `reciper/data/command_mappings.yaml`

---

## 📊 Пример вывода

```bash
$ reciper analyze ./rna-seq-pipeline --verbose

Performance settings: parallel=True, max_workers=None, cache=True
Scanning directory: ./rna-seq-pipeline
Looking for Python files...
  Scanning... Directories: 5, Files: 23, Python files: 8
Found 8 Python files in ./rna-seq-pipeline

Parsing imports from all files...
Aggregated 15 unique packages from 8 files

Looking for dependency files...
Found dependency file: requirements.txt
Parsed 12 package requirements
Warning: 3 imported packages missing from requirements:
  - pysam
  - pybedtools
  - sklearn

Mapping Python packages to conda specifications...
Mapped to 12 conda specifications

Generating files in ....
Scanning for subprocess calls to external tools...
Detected commands: fastqc, samtools, bwa, multiqc

============================================================
PACKAGE CONFLICT DETECTION
============================================================
Detected 2 potential conflict(s):

1. [ERROR] pandas 2.0.0+ requires NumPy 1.21.0+
   Packages involved: pandas, numpy
2. [WARNING] For optimal performance, use numpy>=1.21.0 with pandas>=1.3.0
   Packages involved: numpy, pandas
============================================================

⚠️  Found 1 critical conflict(s) that may cause installation failures.
   Consider adjusting package versions or splitting environments.

Created environment.yml at environment.yml
Created Dockerfile at Dockerfile
Created conda lock file: environment.lock.yml

============================================================
VERIFICATION
============================================================
✓ Dockerfile syntax check passed
✓ environment.yml syntax check passed
✓ Docker container test passed (imports verified)
✅ Verification passed

============================================================
ANALYSIS SUMMARY
============================================================
Directory analyzed: ./rna-seq-pipeline
Python files scanned: 8
Unique packages found: 15
Requirements parsed: 12 packages
Conda specifications generated: 12
Apt packages detected: 4 (samtools, bwa, fastqc, multiqc)
============================================================
Success
```

---

## 💻 Программный API

Reciper можно использовать в своих скриптах:

### Базовый анализ

```python
from reciper import analyze

# Быстрый анализ
result = analyze("./my_pipeline")
print(f"Найдено пакетов: {len(result.imports)}")
print(f"Сгенерировано файлов: {result.generated_files}")

# С JSON выводом
json_result = analyze("./my_pipeline", json_output=True)
print(json_result)
```

### Продвинутый анализ с кастомной конфигурацией

```python
from reciper import Analyzer, AnalysisConfig

config = AnalysisConfig(
    output_dir="./output",
    enable_conflict_check=True,
    enable_verification=True,
    parallel_processing=True,
)

analyzer = Analyzer(config)
result = analyzer.analyze("/path/to/project")

# Доступ к результатам
print(f"Просканировано файлов: {result.scanned_files}")
print(f"Conda пакеты: {list(result.conda_packages.keys())}")
print(f"Apt пакеты: {list(result.apt_packages.keys())}")
print(f"Конфликты: {result.conflicts}")
```

### Использование класса Analyzer

```python
from reciper import Analyzer, AnalysisConfig

# Кастомная конфигурация
config = AnalysisConfig(
    output_dir="./output",
    enable_conflict_check=True,
    enable_verification=True,
    parallel_processing=True,
)

# Создание экземпляра
analyzer = Analyzer(config)

# Анализ директории
result = analyzer.analyze("/path/to/project")

# Доступ к результатам
print(f"Просканировано файлов: {result.scanned_files}")
print(f"Conda пакеты: {len(result.conda_packages)}")
print(f"Apt пакеты: {len(result.apt_packages)}")

# Конвертация в dict или JSON
result_dict = result.to_dict()
result_json = result.to_json(indent=2)
```

### Продвинутая конфигурация

```python
from reciper import AnalysisConfig, analyze_with_custom_config

# Custom configuration for specific use cases
config = AnalysisConfig(
    output_dir="./custom_output",
    generate_dockerfile=True,
    generate_environment_yml=True,
    generate_lockfile=False,  # Skip lockfile generation
    enable_conflict_check=True,
    enable_verification=False,  # Skip verification
    parallel_processing=True,
    max_workers=4,  # Limit parallel workers
    use_cache=True,  # Enable AST caching
    json_output=False,
    verbose=True,
)

# Analyze with custom config
result = analyze_with_custom_config("/path/to/project", config)
```

### Анализ одного файла

```python
from reciper import analyze_single_file

# Analyze a single Python file
result = analyze_single_file("script.py")
print(f"Imports in file: {[imp.module for imp in result.imports]}")
```

### Интеграция с существующим кодом

```python
from reciper import Analyzer
from pathlib import Path

def analyze_project_and_generate_report(project_path: Path) -> dict:
    """Analyze project and return formatted report."""
    analyzer = Analyzer()
    result = analyzer.analyze(project_path)

    # Custom processing
    report = {
        "project": str(project_path),
        "summary": {
            "files_scanned": result.scanned_files,
            "python_files": result.python_files_found,
            "conda_packages": len(result.conda_packages),
            "apt_packages": len(result.apt_packages),
            "conflicts_found": len(result.conflicts),
        },
        "packages": list(result.conda_packages.keys()),
        "generated_files": result.generated_files,
        "verification_passed": result.verification_passed,
    }

    return report

# Usage
report = analyze_project_and_generate_report(Path("./my_project"))
print(report)
```

---

## 🛠️ Технические особенности

### Статический анализ
- **Рекурсивное сканирование** — поиск .py файлов во всех поддиректориях
- **AST парсинг** — извлечение import statements с корректной обработкой синтаксиса
- **Сравнение с requirements.txt** — обнаружение отсутствующих зависимостей
- **Прогресс в реальном времени** — отображение прогресса сканирования
- **Кэширование AST** — ускорение повторных запусков

### Маппинг пакетов
- **Умный маппинг** — конвертация Python → conda с учетом алиасов (sklearn → scikit-learn)
- **Версионные ограничения** — сохранение версий из requirements.txt (>=, ==, <=)
- **Стандартная библиотека** — автоматическое определение builtin модулей
- **100+ биоинформатических пакетов** — biopython, pysam, pybedtools и др.

### Обнаружение системных команд
- **subprocess анализ** — детектирование вызовов через subprocess.run/call/Popen
- **os.system парсинг** — поддержка строковых команд
- **80+ маппингов команд** — samtools, bwa, fastqc, bowtie2 и др.
- **Автоматический apt** — добавление системных пакетов в Dockerfile

### Проверка конфликтов
- **Анализ совместимости** — проверка версионных требований между пакетами
- **Предупреждения об ошибках** — выявление критических конфликтов до сборки
- **Рекомендации** — предложения по оптимальным версиям

### Валидация окружения
- **Docker синтаксис** — проверка корректности Dockerfile
- **Conda синтаксис** — валидация environment.yml
- **Тестовая сборка** — опциональная сборка контейнера для проверки
- **Импорт тест** — верификация импортов внутри контейнера

---

## 📁 Структура проекта

```
reciper/
├── reciper/                    # Основной пакет
│   ├── __init__.py            # Инициализация пакета
│   ├── api.py                 # Публичный API
│   ├── cli.py                 # CLI интерфейс (Click)
│   ├── parser.py              # Парсинг Python импортов (AST)
│   ├── mapper.py              # Маппинг Python → conda
│   ├── generator.py           # Генерация Dockerfile и environment.yml
│   ├── import_aggregator.py   # Агрегация импортов по файлам
│   ├── requirements_parser.py # Парсинг requirements.txt
│   ├── reporter.py            # JSON отчеты
│   ├── scanner.py             # Рекурсивное сканирование
│   ├── verifier.py            # Валидация окружения
│   ├── cache.py               # Кэширование AST
│   ├── command_detector.py    # Детектирование subprocess вызовов
│   ├── conflict_detector.py   # Детектирование конфликтов
│   ├── lockfile_generator.py  # Генерация lock-файлов
│   ├── error_handling.py      # Обработка ошибок
│   ├── constants.py           # Константы
│   ├── utils.py               # Утилиты
│   ├── conda_parser.py        # Парсинг conda окружений
│   └── data/                  # Данные маппинга
│       ├── package_mappings.yaml    # Python → conda
│       ├── command_mappings.yaml    # Команды → apt
│       └── known_conflicts.yaml     # Известные конфликты
├── tests/                     # Тесты
├── examples/                  # Примеры проектов
├── docs/                      # Документация
├── pyproject.toml            # Конфигурация проекта
├── environment.yml           # Conda окружение проекта
├── requirements.txt          # Python зависимости
└── README.md                 # Документация
```

---

## 🧪 Установка и запуск

### Быстрая установка

```bash
# Через pip (рекомендуется для пользователей)
pip install reciper

# Через pipx (изолированно)
pipx install reciper

# Для разработки
git clone https://github.com/h335h/reciper
cd reciper
pip install -e ".[dev]"
```

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием кода
pytest --cov=reciper

# Конкретный модуль
pytest tests/test_command_detector.py
```

### Проверка качества кода

```bash
# Линтер
ruff check reciper/

# Форматирование
black reciper/

# Типизация
mypy reciper/
```

---

## 🔧 Конфигурация

### Маппинг пакетов

Reciper использует YAML файлы для маппинга:

**`reciper/data/package_mappings.yaml`**:
```yaml
primary_mappings:
  numpy: "numpy"
  pandas: "pandas"
  biopython: "biopython"
  scikit-learn: "scikit-learn"

standard_library:
  os: ""
  sys: ""
  pathlib: ""
```

**`reciper/data/command_mappings.yaml`**:
```yaml
samtools: samtools
bwa: bwa
fastqc: fastqc
bowtie2: bowtie2
```

Вы можете расширять маппинги, редактируя эти файлы или создавая свои.

---

## 📖 Подробные примеры использования

### Анализ биоинформатического проекта

```bash
# Базовый анализ с отображением прогресса
reciper analyze ./my_bioinformatics_project

# Генерация файлов в указанной директории
reciper analyze ./my_bioinformatics_project --output ./environments

# JSON отчет для программной обработки
reciper analyze ./my_bioinformatics_project --json --report-file analysis.json
```

### Анализ одного файла

```bash
# Анализ отдельного Python файла
reciper analyze script.py

# Анализ с кастомным выводом
reciper analyze pipeline.py --output ./docker
```

---

## 📊 Структура JSON отчета

Инструмент генерирует подробные JSON отчеты со следующей структурой:

```json
{
  "scan_summary": {
    "scan_directory": "/path/to/project",
    "total_files_scanned": 42,
    "python_files_found": 15,
    "scan_time_seconds": 1.234,
    "scan_timestamp": "2024-01-15T10:30:00Z"
  },
  "detected_imports": [
    "numpy",
    "pandas",
    "matplotlib",
    "biopython",
    "scikit-learn"
  ],
  "requirements_analysis": {
    "requirements_file_found": true,
    "requirements_file_path": "/path/to/project/requirements.txt",
    "parsed_requirements_count": 8,
    "imports_missing_from_requirements": ["biopython"],
    "requirements_not_imported": ["flask", "requests"]
  },
  "package_mapping": [
    {
      "python_package": "numpy",
      "conda_package": "numpy",
      "version_constraint": ">=1.21.0",
      "mapping_source": "primary_mappings"
    },
    {
      "python_package": "biopython",
      "conda_package": "biopython",
      "version_constraint": null,
      "mapping_source": "primary_mappings"
    }
  ],
  "generated_files": {
    "dockerfile": {
      "generated": true,
      "path": "/path/to/project/Dockerfile"
    },
    "environment_yml": {
      "generated": true,
      "path": "/path/to/project/environment.yml"
    }
  },
  "warnings": [
    "3 imported packages missing from requirements"
  ]
}
```

---

## 🚀 Как это работает?

1. **Сканирование**: Инструмент рекурсивно сканирует целевую директорию на наличие Python файлов
2. **Парсинг**: Каждый Python файл парсится для извлечения import statements
3. **Агрегация**: Импорты агрегируются по всем файлам, удаляя дубликаты
4. **Анализ требований**: Если существует requirements.txt, он парсится и сравнивается с обнаруженными импортами
5. **Маппинг**: Имена Python пакетов маппятся на имена conda пакетов с использованием базы данных маппингов
6. **Генерация**: Файлы Dockerfile и environment.yml генерируются с замаппленными пакетами
7. **Отчетность**: Генерируется подробный JSON отчет (если запрошено)

---

## ⚠️ Ограничения и будущие улучшения

### Текущие ограничения
- Поддерживает только Python импорты (не другие языки)
- Базовая обработка версионных ограничений
- Ограничено conda и Docker генерацией окружений
- Единый файл маппингов (не динамически обновляемый)

### Планируемые функции
- Поддержка дополнительныхых менеджеров пакетов (pip, apt, и др.)
- Динамическое обновление маппингов из репозиториев conda
- Поддержка R и других биоинформатических языков
- Интеграция с CI/CD пайплайнами
- Веб-интерфейс для визуализации

---

## 🤝 Участие в разработке

Вклад в проект приветствуется! Смотрите раздел установки для разработки выше, чтобы начать.

1. Форкните репозиторий
2. Создайте feature ветку
3. Внесите изменения
4. Добавьте тесты для нового функционала
5. Убедитесь, что все тесты проходят
6. Отправьте pull request

---

## 📄 Лицензия

MIT
