# Дубль — Telegram Mini App для озвучки сцен

Каталог сцен из фильмов, где пользователь записывает свою реплику (или
загружает готовый аудиофайл) и получает смонтированное видео, где
оригинальная озвучка заменена (или смешана) с его голосом через FFmpeg.

```
telegram-dubbing-app/
├── frontend/
│   └── index.html          # Mini App: каталог, запись/загрузка аудио, отправка на бэкенд
└── backend/
    ├── main.py              # FastAPI: /api/scenes, /api/scenes/{id}/dub
    ├── ffmpeg_utils.py       # обёртка над ffmpeg CLI (replace / mix)
    ├── models.py             # pydantic-модели Scene и DubResponse
    ├── requirements.txt
    └── storage/
        ├── videos/           # исходные видео сцен, например 0.mp4, 1.mp4 ...
        ├── uploads/           # сырые аудиозаписи пользователей
        └── output/            # готовые смонтированные видео
```

## Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# ffmpeg должен быть установлен на сервере:
# macOS:   brew install ffmpeg
# Ubuntu:  apt-get install ffmpeg

uvicorn main:app --reload --port 8000
```

Положите исходные видео сцен в `backend/storage/videos/` с именами,
указанными в поле `video_file` каждой `Scene` в `main.py` (например `0.mp4`).

### Эндпоинты

| Метод | Путь                          | Описание                                    |
|-------|-------------------------------|----------------------------------------------|
| GET   | `/api/scenes`                 | список всех сцен каталога                    |
| GET   | `/api/scenes/{id}`            | одна сцена                                   |
| POST  | `/api/scenes/{id}/dub`        | принимает `audio` (multipart) и `init_data`, возвращает `output_url` смонтированного видео |
| GET   | `/media/output/<file>.mp4`    | статика: готовые ролики                      |

`main.py` сейчас хранит каталог сцен в памяти (`SCENES = [...]`) — замените
это на запрос к вашей БД, когда появится реальный контент.

## Frontend (Mini App)

`frontend/index.html` — самодостаточный файл, ничего собирать не нужно.

1. В самом файле в `<script>` замените
   `const API_BASE = window.DUB_API_BASE || 'https://your-backend.example.com';`
   на адрес вашего задеплоенного бэкенда (обязательно HTTPS — Telegram не
   откроет Mini App по HTTP).
2. Захостите `index.html` на любом HTTPS-хостинге (Vercel, Netlify,
   GitHub Pages, nginx на своём сервере и т.п.).
3. В [@BotFather](https://t.me/BotFather) выполните `/newapp` для вашего
   бота и укажите URL этого файла — Telegram откроет его как Mini App
   внутри клиента.

Файл уже подключает `telegram-web-app.js` и использует `Telegram.WebApp`
(тема, `BackButton`, `HapticFeedback`, `initData`), так что достаточно
открыть его через бота — специальной сборки не требуется.

## Как это работает

1. Пользователь открывает сцену в каталоге → видит превью видео.
2. Записывает голос через `MediaRecorder` (браузерный API, работает в
   Telegram WebView) или выбирает готовый аудиофайл.
3. Файл отправляется `multipart/form-data` на
   `POST /api/scenes/{id}/dub`.
4. Бэкенд сохраняет аудио, запускает `ffmpeg` (`ffmpeg_utils.py`) и либо
   **полностью заменяет** аудиодорожку видео (`mode="replace"`), либо
   **смешивает** голос пользователя с фоном/музыкой оригинала
   (`mode="mix"`, регулируется громкость через `volume=`).
5. Готовый ролик кладётся в `storage/output/` и отдаётся статикой по
   `output_url` — фронтенд показывает ссылку на результат.

## Что стоит добавить перед продакшеном

- Проверку `init_data` по алгоритму Telegram (подпись HMAC токеном бота),
  сейчас поле только принимается, но не валидируется.
- Очередь для рендера (Celery/RQ), если сцены длинные или нагрузка растёт —
  сейчас `ffmpeg` вызывается синхронно внутри запроса.
- Хранение видео/результатов в object storage (S3-совместимом), а не на
  локальном диске.
- Ограничение размера и длительности загружаемого аудио.
