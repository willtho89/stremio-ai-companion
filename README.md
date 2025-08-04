# Stremio AI Companion

🎬 Your AI-powered movie and tv series discovery companion for Stremio — powered by advanced natural language understanding using OpenAI compatible APIs. Discover perfect films using intelligent recommendations and (soon) AI-curated collections.

![Demo Screenshot](.assets/stremio-ai-companion.gif)

---

## ✨ Features

- 🧠 Natural language movie & series search: e.g. “feel-good sci-fi from the 90s”
- 🎯 Smart AI recommendations based on mood and context
- 🎨 Detailed movie & TV data from TMDB + optional enhanced artwork from RPDB
- ⚡ Fast response time — typically 5–6 seconds per query
- 🔐 100% privacy-first: encrypted, stateless config via shareable URLs
- 🎞️ Split manifest support: Movies, Series, or both (toggleable)
- 🧺 Curated Collections (coming soon): AI-crafted picks by theme, mood, genre
- 🧩 Native Stremio support: works as a catalog addon (movies, series, and catalogs)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get API Keys

- 🔑 AI Provider Key (choose one):
  - [OpenAI](https://platform.openai.com/account/api-keys)
  - [OpenRouter](https://openrouter.ai/keys) — supports 400+ models incl. Claude, Gemini, GPT-4
- 🎬 TMDB API Key — [Create free key](https://developer.themoviedb.org/docs)
- 🖼️ RPDB API Key (optional) — [Sign up](https://ratingposterdb.com/)

### 3. Run the Server

```bash
python main.py
# or with uvicorn:
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Configure Your Companion

1. Visit http://localhost:8000
2. Click "Configure Your AI Companion"
3. Enter API keys and preferences
4. Copy the generated manifest URL
5. Paste it into Stremio as a new addon

---

## 🧠 How It Works

1. Describe what you want to watch.
2. AI understands your request, extracts intent.
3. Suggests clever matches using natural language & GPT-style models.
4. Metadata enriched with TMDB for movies and TV.
5. Beautiful artwork (optional) via RPDB.

Examples:

- “films like Inception and The Matrix”
- “tv shows like True Detective season 1”
- “lighthearted rom-coms from Europe”
- “space horror set on abandoned ships”
- “Oscar wins for best cinematography”

---

## 🌐 Deployment

### Docker (Simple Run)

```bash
docker build -t stremio-ai-companion .
docker run -d \
  -p 8000:8000 \
  -e ENCRYPTION_KEY="your-strong-key" \
  ghcr.io/willtho89/stremio-ai-companion:latest
```

### Docker Compose (Recommended)

```bash
docker compose up -d
```

Customize with a .env file:
```env
ENCRYPTION_KEY=replace-this-key
OPENAI_API_KEY=your-openai-key
TMDB_API_KEY=your-tmdb-key
RPDB_API_KEY=optional
# Optional features
ENABLE_FEED_CATALOGS=true
# Redis (optional). If set, enables shared caching
# or use discrete host settings
# REDIS_HOST=redis
# REDIS_PORT=6379
# REDIS_DB=0
```

---

## ⚙️ Environment Variables

| Variable               | Description                                | Default                        |
|------------------------|--------------------------------------------|--------------------------------|
| ENCRYPTION_KEY         | AES-256 encryption key (required)          | —                              |
| OPENAI_API_KEY         | OpenAI or OpenRouter key                   | —                              |
| OPENAI_BASE_URL        | AI model gateway URL                       | https://openrouter.ai/api/v1   |
| DEFAULT_MODEL          | e.g. openrouter/horizon-beta:online        | openrouter/horizon-beta:online |
| TMDB_API_KEY           | TMDB token                                 | —                              |
| RPDB_API_KEY           | RPDB artwork key (optional)                | —                              |
| MAX_CATALOG_RESULTS    | Search result cap                          | 50                             |
| SPLIT_MANIFESTS        | Enable movies-only/series-only manifests   | false                          |
| FOOTER_ENABLED         | Show footer in web interfaces              | true                           |
| HOST                   | Server bind host                           | 0.0.0.0                        |
| PORT                   | Server port                                | 8000                           |
| UVICORN_WORKERS        | Uvicorn worker count (0 = auto)            | 0                              |
| ENABLE_FEED_CATALOGS   | Expose predefined AI-curated catalogs       | true                           |
| REDIS_HOST             | Redis host (if no URL)                      | redis                          |
| REDIS_PORT             | Redis port                                  | 6379                           |
| REDIS_DB               | Redis database index                        | 0                              |

---

## 📡 Stremio Manifest & Catalog URLs

- 🔗 Default combined:  
  `/config/{CONFIG}/adult/{0|1}/manifest.json`
- 🎬 Movies only:  
  `/config/{CONFIG}/adult/{0|1}/movie/manifest.json`
- 📺 Series only:  
  `/config/{CONFIG}/adult/{0|1}/series/manifest.json`
- 🧺 Curated catalogs (movies & series):
  `/config/{CONFIG}/adult/{0|1}/catalog/{movie|series}/{catalog_id}.json`
  `/config/{CONFIG}/adult/{0|1}/catalog/{movie|series}/{catalog_id}/skip={N}.json`
  `/config/{CONFIG}/adult/{0|1}/catalog/{movie|series}/{catalog_id}/search={QUERY}.json`

Use the preview dropdown to copy them.

---

## 🛠️ API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET    | /                      | Home + description |
| GET    | /configure             | New configuration form |
| GET    | /configure?config=... | Edit encrypted URL |
| POST   | /save-config           | Returns a manifest URL |
| GET    | /config/.../preview    | Human preview of config |
| GET    | /config/.../adult/{0|1}/manifest.json | Combined manifest |
| GET    | /config/.../adult/{0|1}/movie/manifest.json | Movies-only manifest |
| GET    | /config/.../adult/{0|1}/series/manifest.json | Series-only manifest |
| GET    | /config/.../adult/{0|1}/catalog/{movie|series}/{catalog_id}.json | Curated catalog entries |
| GET    | /config/.../adult/{0|1}/catalog/{movie|series}/{catalog_id}/search=... | Catalog search queries |

---

## 🔐 Security & Config Storage

- AES-256 GCM encryption + PBKDF2
- Configuration embedded in URL — no server-side storage
- Your API keys stay local and never stored

---

## 🎭 Split Manifest Support

Available from v0.2.0+. Flexible manifest structure:

- 🧩 Use a single addon or split into:
  - Movies-only addon
  - Series-only addon
  - Combined one

👍 Great for power users who want focused discovery or cleaner interfaces.

---

## 🧪 Testing

```bash
pip install -r requirements-dev.txt
pytest
pytest --cov=app  # with coverage report
```

See [tests/README.md](tests/README.md) for more.

---

## 🤝 Contributing

Contributions welcome — follow the standard GitHub workflow!

1. Fork 📌
2. Create a new feature branch 🚧
3. Make changes and test thoroughly 🧪
4. Create a pull request 🔄

Please ensure test coverage for new features.

---

## 📄 License

MIT — See [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- [Stremio](https://www.stremio.com/) — media discovery reimagined
- [stremio-ai-search](https://github.com/itcon-pty-au/stremio-ai-search) - inspiration for this addon
- [TMDB](https://themoviedb.org) — open movie & TV metadata platform
- [OpenRouter](https://openrouter.ai) — model routing + GPT ecosystem
- [RatingPosterDB](https://ratingposterdb.com/) — gorgeous cinematic posters
- [OpenAI](https://openai.com/) — large language models
- [standard-readme](https://github.com/RichardLitt/standard-readme) — best practices for READMEs [github.com](https://github.com)
- [makeareadme.com](https://www.makeareadme.com/) — more docs advice and layout tips

---
