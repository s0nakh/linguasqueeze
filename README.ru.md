<div align="center">

<img src="https://raw.githubusercontent.com/s0nakh/linguasqueeze/main/assets/banner.png" alt="LinguaSqueeze" width="720">

## Сжимай под свой язык, а не только под своё железо.

**Квантование с учётом языка для многоязычных MoE-моделей.**
Сжатая модель может хорошо выглядеть по одной средней оценке и при этом терять менее распространённый язык. LinguaSqueeze калибрует на текстах *вашего* языка, отдаёт больше бит экспертам, которыми ваш язык действительно пользуется, и показывает, что ваш язык потерял. На Qwen3-30B-A3B выбор бит и калибровки по английскому тексту при той же памяти вредит казахскому в 16 раз сильнее.
Первое доказательство — казахский 🇰🇿 и русский 🇷🇺 на Qwen3-30B-A3B: 61 ГБ → 15,24 ГБ, перплексия казахского +1,3%, на одной бесплатной видеокарте Kaggle.<br>
Перевод с английского на казахский при том же размере: **+5,5 chrF** к файлу, сжатому под английский.

<sub>Раньше назывался <b>LinguaPrune</b>: переименован 20.11.2026, потому что метод в основном сжимает экспертов в меньшее число бит, а не удаляет их. Старые ссылки и <code>import linguaprune</code> продолжают работать.</sub>

<p>
<a href="https://github.com/s0nakh/linguasqueeze/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-A020F0?style=for-the-badge&labelColor=0D1117&logo=apache&logoColor=white"></a>
<a href="https://github.com/s0nakh/linguasqueeze/actions/workflows/tests.yml"><img alt="Tests" src="https://img.shields.io/github/actions/workflow/status/s0nakh/linguasqueeze/tests.yml?style=for-the-badge&labelColor=0D1117&logo=githubactions&logoColor=white&label=tests"></a>
<a href="https://github.com/s0nakh/linguasqueeze"><img alt="Stars" src="https://img.shields.io/github/stars/s0nakh/linguasqueeze?style=for-the-badge&labelColor=0D1117&logo=github&color=A020F0"></a>
<a href="https://github.com/s0nakh/linguasqueeze/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/s0nakh/linguasqueeze?style=for-the-badge&labelColor=0D1117&logo=git&logoColor=white&color=39FF14"></a>
<a href="#roadmap"><img alt="Status" src="https://img.shields.io/badge/status-research%20preview-FF8C00?style=for-the-badge&labelColor=0D1117&logo=jupyter&logoColor=white"></a>
</p>
<p>
<a href="https://pypi.org/project/linguasqueeze/"><img alt="PyPI" src="https://img.shields.io/pypi/v/linguasqueeze?style=for-the-badge&labelColor=0D1117&logo=pypi&logoColor=white&color=39FF14"></a>
<a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-39FF14?style=for-the-badge&labelColor=0D1117&logo=python&logoColor=white"></a>
<a href="https://pytorch.org/"><img alt="PyTorch" src="https://img.shields.io/badge/PyTorch-2.x-EE4C2C?style=for-the-badge&labelColor=0D1117&logo=pytorch&logoColor=white"></a>
<a href="https://github.com/huggingface/transformers"><img alt="Transformers" src="https://img.shields.io/badge/Transformers-5.x-FFD21E?style=for-the-badge&labelColor=0D1117&logo=huggingface&logoColor=white"></a>
<a href="https://www.kaggle.com/"><img alt="Kaggle" src="https://img.shields.io/badge/Kaggle-free%20T4-20BEFF?style=for-the-badge&labelColor=0D1117&logo=kaggle&logoColor=white"></a>
</p>
<p>
<a href="https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507"><img alt="Model" src="https://img.shields.io/badge/model-Qwen3--30B--A3B-F0529C?style=for-the-badge&labelColor=0D1117&logo=huggingface&logoColor=white"></a>
<a href="#citation"><img alt="Cite" src="https://img.shields.io/badge/cite-BibTeX-00BFFF?style=for-the-badge&labelColor=0D1117&logo=googlescholar&logoColor=white"></a>
<a href="#evaluation"><img alt="Eval" src="https://img.shields.io/badge/eval-KazMMLU%20%C2%B7%20Belebele-00C2FF?style=for-the-badge&labelColor=0D1117&logo=meta&logoColor=white"></a>
<a href="#evaluation"><img alt="Languages" src="https://img.shields.io/badge/languages-kk%20%C2%B7%20ru-39FF14?style=for-the-badge&labelColor=0D1117&logo=googletranslate&logoColor=white"></a>
<a href="https://github.com/s0nakh/linguasqueeze/blob/main/README.ru.md"><img alt="Docs" src="https://img.shields.io/badge/docs-EN%20%C2%B7%20RU%20%C2%B7%20KK-A020F0?style=for-the-badge&labelColor=0D1117&logo=readthedocs&logoColor=white"></a>
<a href="https://doi.org/10.5281/zenodo.24281163"><img alt="Paper" src="https://img.shields.io/badge/%D1%81%D1%82%D0%B0%D1%82%D1%8C%D1%8F-Zenodo-1682D4?style=for-the-badge&labelColor=0D1117&logo=zenodo&logoColor=white"></a>
</p>

<p><a href="https://github.com/s0nakh/linguasqueeze/blob/main/RESEARCH.ru.md"><img alt="исследование и полная история" src="https://img.shields.io/badge/%F0%9F%93%9A_%D0%B8%D1%81%D1%81%D0%BB%D0%B5%D0%B4%D0%BE%D0%B2%D0%B0%D0%BD%D0%B8%D0%B5_%D0%B8_%D0%BF%D0%BE%D0%BB%D0%BD%D0%B0%D1%8F_%D0%B8%D1%81%D1%82%D0%BE%D1%80%D0%B8%D1%8F-%D0%BE%D1%82%D0%BA%D1%80%D1%8B%D1%82%D1%8C_%E2%86%92-A020F0?style=for-the-badge&labelColor=0D1117"></a></p>
🇬🇧 [English](https://github.com/s0nakh/linguasqueeze/blob/main/README.md) · 🇰🇿 [Қазақша](https://github.com/s0nakh/linguasqueeze/blob/main/README.kk.md) · [Исследовательский журнал](https://github.com/s0nakh/linguasqueeze/blob/main/docs/research-log.ru.md) · [Связанные работы](https://github.com/s0nakh/linguasqueeze/blob/main/docs/prior-art.ru.md)

</div>

---

**Содержание:** [Результаты](#result) · [Как это работает](#how) · [Быстрый старт](#quick-start) · [Для кого](#who) · [Дорожная карта](#roadmap) · [Ограничения](#limitations) · [Исследование](https://github.com/s0nakh/linguasqueeze/blob/main/RESEARCH.ru.md) · [Цитирование](#citation)

<a id="result"></a>
<a id="evaluation"></a>
## 📊 Доказано на Qwen3-30B-A3B

Каждая цифра получена из записанного файла на фиксированном экзамене; данные и скрипты лежат в репозитории.

|  | Что измеряли | Результат | Источник |
|---|---|---|---|
| ✅ | Размер файла | **61,1 → 15,24 ГБ (в 4,0 раза меньше)** | ноутбук 07 |
| ✅ | Казахский / русский текст (рост перплексии) | **+1,3% / +0,4%** | ноутбук 07 |
| ✅ | Если калибровать на английском, тот же размер | казахскому **в 16 раз хуже** (+14,3% против +0,9%) | ноутбук 06 |
| ✅ | Перевод с английского на казахский, тот же размер | **+5,5 chrF** [+3,9; +7,1] к файлу, сжатому под английский | experiments/translation |
| ✅ | Популярные файлы GGUF около 15 ГБ | ближайший: казахский +4,3%; наш **+1,3%** | ноутбук 09 |
| ⚠️ | Знания, полный KazMMLU (22 889 вопросов) | −1,8 / −1,6 пункта (kk / ru) | ноутбук 07b |

<a id="how"></a>
## ⚙️ Как это работает

1. 📝 **Текст на вашем языке** — достаточно нескольких десятков документов.
2. 🔀 **Профиль маршрутизатора** — какие эксперты MoE-модели этот язык действительно использует, слой за слоем.
3. 🎚️ **Распределение бит** — экспертам, на которых приходится 90% трафика языка, 4 бита, остальным 3.
4. 🧮 **GPTQ для каждого эксперта** — калибровка на токенах вашего языка, попавших к этому эксперту.
5. 📦 **Стандартный файл GPTQ** — пишется по одному слою, поэтому модель на 61 ГБ обрабатывается на одной видеокарте с 16 ГБ.
6. 📊 **Проверка** — исходная и сжатая модель на одних и тех же вопросах: что потерял ваш язык.

<a id="quick-start"></a>
## 🚀 Быстрый старт

```bash
pip install linguasqueeze
linguasqueeze --version   # linguasqueeze 0.8.2
```

```bash
# 1. compress: калибровка на вашем языке; эксперты, на которых приходится 90% его трафика, получают 4 бита, остальные 3
linguasqueeze compress \
  --model ./Qwen3-30B-A3B-Instruct-2507 \
  --calibration-data kazakh.txt russian.txt \
  --bits 4,3 \
  --output ./qwen3-30b-kk-ru

# 2. evaluate: одни и те же вопросы для обеих моделей; каждая цифра сжатой модели — из её файлов
linguasqueeze evaluate \
  --original ./Qwen3-30B-A3B-Instruct-2507 \
  --compressed ./qwen3-30b-kk-ru \
  --text kk=kazakh_test.txt --text ru=russian_test.txt \
  --exam --report report.json
```

Файлы для калибровки и проверки — обычный текст UTF-8, документы разделены пустой строкой. Команда принимает текст на любом языке; качество измерено только для казахского и русского.
`--exam` добавляет фиксированный экзамен ноутбука 07: Belebele (по 150 текстов на kk, ru, en) и выборку KazMMLU по 400 вопросов на язык (kk, ru). Цифры KazMMLU ниже получены на полном экзамене (22 889 вопросов, ноутбук 07b), поэтому на выборке выйдут немного другие значения. Быстрый экзамен намеренно небольшой, чтобы уложиться во время Kaggle; для цифр KazMMLU уровня публикации используйте ноутбук 07b. `compress` и `evaluate` загружают модель по одному слою, поэтому исходная модель на 61 ГБ обрабатывается на одной видеокарте с 16 ГБ; сколько памяти нужно для запуска сжатой модели, зависит от программы запуска и длины контекста.
Пока поддерживаются: `compress` — Qwen3-MoE в формате safetensors (полный прогон на Qwen3-30B-A3B); `evaluate` — Qwen3-MoE и Qwen3.5/3.6-MoE.

Что выдаёт `evaluate` (сокращённо), с цифрами, которые мы получили для Qwen3-30B-A3B тем же кодом ([ноутбук 07](https://github.com/s0nakh/linguasqueeze/blob/main/notebooks/07_real_gptq_checkpoint.py), [07b](https://github.com/s0nakh/linguasqueeze/blob/main/notebooks/07b_full_kazmmlu.py)):

```
Original size:     61.1 GB
Compressed size:   15.2 GB
Compression:       4.0x
Perplexity kk:     +1.3%
Perplexity ru:     +0.4%
KazMMLU kk:        -1.8 pts
KazMMLU ru:        -1.6 pts
```

**Эти две команды, запущенные на Qwen3-30B-A3B** (одна T4 на Kaggle, 43 мин на `compress`, 49 мин на `evaluate`): файл 15,24 ГБ, в 4,0 раза меньше; перплексия Belebele kk +0,6%, ru +0,4%, en +4,0%; выборка KazMMLU kk −0,8 п. [−3,5; +1,9], ru −1,5 п. [−4,3; +1,0] (370 + 392 вопроса). Статьи для калибровки — те же, что в ноутбуке 07, но с убранными пустыми строками, поэтому цифры близки к ноутбуку 07, но не совпадают. Отчёт и скрипт: [`experiments/cli/`](https://github.com/s0nakh/linguasqueeze/blob/main/experiments/cli/).

Скорость и память при работе модели зависят от программы запуска, поэтому `evaluate` их не угадывает: измеряйте там.

## 📍 Что есть сейчас (v0.8.2)

**Уже работает:** `linguasqueeze compress` для Qwen3-MoE · `linguasqueeze evaluate` для Qwen3-MoE и Qwen3.5/3.6-MoE · смешанный экспорт 4/3 бита в стандартном формате GPTQ · калибровка по обычному тексту на любом языке · по желанию экзамен Belebele + KazMMLU · отчёт в JSON.

**Пока нет:** запуска файлов со смешанной разрядностью в vLLM, llama.cpp, Ollama или LM Studio · сжатия Qwen3.5/3.6-MoE · обычных (не MoE) моделей · замеров скорости и памяти сжатой модели.

<a id="who"></a>
## 👥 Для кого и зачем

Инструмент, который помогает небольшой команде сжать большую модель под свой язык на доступном оборудовании — и увидеть, что этот язык потерял после сжатия.

- **Разработчикам моделей** — сжать открытую модель под язык своих пользователей и проверить её до выпуска.
- **Исследователям и университетам** — воспроизводимые замеры по каждому языку: размер, перплексия, экзамен — с погрешностью.
- **Небольшим командам** — без дорогих видеокарт: сжатие и проверку исходной модели можно запустить на одной видеокарте с 16 ГБ, например бесплатной на Kaggle. Память для запуска готовой модели зависит от программы запуска.
- **Любому языку** — казахский, узбекский, арабский, хинди, украинский, вьетнамский: нужен только текст на своём языке. Качество пока измерено для казахского и русского.

> **Зачем:** сжатие обычно оценивают по размеру и скорости. LinguaSqueeze показывает ещё и то, что после сжатия случилось с вашим языком.



<a id="roadmap"></a>
## 🗺️ Дорожная карта

**✅ Сделано**

| 🔢 № | 🧪 Шаг | 📈 Результат |
|---|---|---|
| ✅ 01–05 | Профиль маршрутизации, прунинг, смешанная точность, GPTQ на OLMoE | метод, собранный на небольшой MoE |
| ✅ 06 | Qwen3-30B-A3B: английский против kk+ru при той же памяти | английский обходится казахскому в **16 раз** дороже по перплексии |
| ✅ 07 | Настоящий сжатый файл, оценка с диска | **61,1 → 15,24 ГБ (в 4,0 раза)**, kk +1,3%, ru +0,4% |
| ✅ 07b | Полный KazMMLU (22 889 вопросов) | −1,8 / −1,6 пункта (4/3 бита), −1,1 / −0,4 (4 бита) |
| ✅ 07c | Дело ли в распределении бит? | да: самые используемые эксперты kk +1,3%, случайные +3,5…+5,0%, самые редкие +6,3% |
| ✅ 08 | Файл в GPTQModel | отвечает на kk, ru и en; перплексия совпадает с 07 в пределах 0,1% |
| ✅ 09 | Против 9 популярных файлов GGUF | впереди около 15 ГБ (+1,3% против +4,3% у ближайшего); на 17–18 ГБ ничья |
| ✅ 10 | Язык калибровки в 2 битах | помогает мало (+18,9% → +15,1%); распределение бит важнее ([журнал](https://github.com/s0nakh/linguasqueeze/blob/main/docs/research-log.ru.md#2026-11-14--10--важен-ли-язык-калибровки-в-2-битах)) |
| ✅ HF | Оба файла открыты на Hugging Face | [4/3 бита](https://huggingface.co/s0nakh/Qwen3-30B-A3B-Instruct-2507-kk-ru-GPTQ-4-3bit), [4 бита](https://huggingface.co/s0nakh/Qwen3-30B-A3B-Instruct-2507-kk-ru-GPTQ-4bit); описания на EN, RU, KK |
| ✅ v0.8 | `linguasqueeze compress` / `evaluate` | любой язык по текстовым файлам; полный прогон на Qwen3-30B-A3B |
| ✅ — | Язык калибровки и знания (Qwen3.6, 3 бита) | разницы нет: KazMMLU kk +0,4 [−1,1; +1,8] |
| ✅ — | Перевод с английского на казахский, тот же размер | **+5,5 chrF** [+3,9; +7,1] у файла, сжатого под kk+ru |

**🚀 Дальше**

| 🚦 Статус | 🧭 Шаг |
|---|---|
| 🔥 сейчас | Файл ~2,5 бита на 10–12 ГБ, где популярные файлы теряют 10–16% казахского |
| ⬜ | Установка одной командой (PyPI) и готовый ноутбук на Kaggle |
| ⬜ | Наш 4-битный файл в движке vLLM, сравнение с популярными файлами в том же движке |
| ⬜ | Экзамен по законам и официальным документам Казахстана (kk, ru) |
| ⬜ | MERA (русский) |
| ⬜ | Вторая пара языков и второе семейство MoE |

<a id="limitations"></a>
## ⚠️ Ограничения

- Главный результат — одна модель (Qwen3-30B-A3B) и один запуск; первая пара языков — казахский и русский. Это не доказательство, что любая модель и любой язык выиграют одинаково.
- Сжатие не без потерь: на полном KazMMLU файл 4/3 бита теряет 1,8 пункта в казахском и 1,6 в русском.
- Язык калибровки не изменил знания. На Qwen3.6-35B-A3B, где все эксперты сжаты до 3 бит (размер одинаковый), калибровка на казахском и русском против английской дала на KazMMLU kk +0,4 пункта [−1,1; +1,8] на 3000 вопросах и ru +1,8 [−0,2; +3,6] на 1200 вопросах — значимой разницы нет. Выигрыш, который мы измеряем, — в том, как модель обращается с текстом на языке (перплексия и качество перевода), а не в знаниях на экзамене. Данные: [`experiments/calibration-language/`](https://github.com/s0nakh/linguasqueeze/blob/main/experiments/calibration-language/).
- На 2 битах язык калибровки помогает мало (потеря казахского +18,9% → +15,1%, ноутбук 10); распределение бит важнее.
- Популярные быстрые программы запуска пока не умеют запускать экспертов одного слоя с разным числом бит. GPTQModel запускает файл, но медленно (около 1,6 токена/с на двух T4).
- `compress` записывает файлы только для устройства Qwen3-MoE; Qwen3.5/3.6-MoE можно оценить через `evaluate`, но пока нельзя сжать. Обычные (не MoE) модели не поддерживаются.
- Наборы данных и модели сохраняют свои лицензии; см. [THIRD_PARTY_NOTICES.md](https://github.com/s0nakh/linguasqueeze/blob/main/THIRD_PARTY_NOTICES.md).

## 🤝 Участие

Больше всего ждём: повторения на других видеокартах и программах запуска, поддержку других MoE-архитектур, тексты для калибровки на других языках (только те, что можно распространять), независимые сравнения и отрицательные результаты — где сжатие с учётом языка не помогает. Сначала откройте issue с минимальным примером воспроизведения.

## 📚 Исследование и полная история

Десять ноутбуков, контрольные опыты, отрицательные результаты и каждое решение по пути: **[открыть страницу исследования →](https://github.com/s0nakh/linguasqueeze/blob/main/RESEARCH.ru.md)**

<a id="paper"></a>
## 📄 Статья

Исследование доступно как препринт (CC BY 4.0) на трёх языках. Английская версия — оригинал; русская и казахская — переводы.

- 🇬🇧 [English](https://doi.org/10.5281/zenodo.24281161)
- 🇷🇺 [Русский](https://doi.org/10.5281/zenodo.24281163)
- 🇰🇿 [Қазақша](https://doi.org/10.5281/zenodo.24281169)

**Как сослаться на статью** (английский оригинал):

```bibtex
@misc{akhmetova2026linguaprune_paper,
  title     = {LinguaPrune: Language-Aware Mixed-Precision Quantization of a Mixture-of-Experts LLM for Kazakh and Russian},
  author    = {Akhmetova, Sophia},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.24281161},
  url       = {https://doi.org/10.5281/zenodo.24281161}
}
```

```text
Akhmetova, S. (2026). LinguaSqueeze: Language-aware mixed-precision quantization of a Mixture-of-Experts LLM for Kazakh and Russian [Preprint]. Zenodo. https://doi.org/10.5281/zenodo.24281161
```

<a id="citation"></a>
## 📝 Цитирование

<p align="center"><a href="#citation"><img alt="Cite this repository" src="https://img.shields.io/badge/cite%20as-BibTeX%20%C2%B7%20APA-00BFFF?style=for-the-badge&labelColor=0D1117&logo=googlescholar&logoColor=white"></a></p>

Если вы используете LinguaSqueeze в своей работе, пожалуйста, сошлитесь на него. У каждого блока ниже есть кнопка копирования; на GitHub то же самое даёт кнопка **Cite this repository** в боковой колонке (данные из [`CITATION.cff`](https://github.com/s0nakh/linguasqueeze/blob/main/CITATION.cff)).

**BibTeX**

```bibtex
@software{linguasqueeze2026,
  title   = {LinguaSqueeze: Language-aware compression for Mixture-of-Experts LLMs},
  author  = {Akhmetova, Sophia},
  year    = {2026},
  version = {0.8.2},
  url     = {https://github.com/s0nakh/linguasqueeze}
}
```

**APA**

```text
Akhmetova, S. (2026). LinguaSqueeze: Language-aware compression for Mixture-of-Experts LLMs (Version 0.8.2) [Computer software]. https://github.com/s0nakh/linguasqueeze
```

## ⚖️ Лицензия

Код распространяется по лицензии [Apache-2.0](https://github.com/s0nakh/linguasqueeze/blob/main/LICENSE). У моделей, датасетов и инструментов свои лицензии; полный список, сверенный с каждым источником, — в [`THIRD_PARTY_NOTICES.md`](https://github.com/s0nakh/linguasqueeze/blob/main/THIRD_PARTY_NOTICES.md). Кратко:

| Ресурс | Лицензия | Как используется здесь |
|---|---|---|
| Qwen3-30B-A3B-Instruct-2507, OLMoE-1B-7B | Apache-2.0 | Модели, которые мы сжимаем и измеряем |
| [Belebele](https://huggingface.co/datasets/facebook/belebele) (Bandarkar и др., ACL 2024) | CC-BY-SA-4.0 | Оценка; публикуются только числа, тексты не распространяются |
| [KazMMLU](https://huggingface.co/datasets/MBZUAI/KazMMLU) (Togmanov и др., ACL 2025) | CC-BY-NC-4.0 | Оценка только для некоммерческого исследования |
| Википедия (kk, ru, en) | CC-BY-SA-3.0 / GFDL | Только калибровочный текст |
| llama.cpp, llama-cpp-python | MIT | Инструменты GGUF и запуск |
