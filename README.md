# Gift Store AI Service

A FastAPI-based AI microservice for an online personalized gift store.  
Provides a conversational chat assistant and semantic product search, powered by OpenAI.

It is one of three parts of the project — the .NET backend calls it, the browser never does:

| Part | Repository | Tech |
|---|---|---|
| 🖥️ Frontend | [sarli-s/shop-frontend](https://github.com/sarli-s/shop-frontend) | Angular 21, PrimeNG |
| ⚙️ Backend API | [sarli-s/APIproject](https://github.com/sarli-s/APIproject) | .NET 9, EF Core, SQL Server, Redis, Kafka |
| 🤖 AI Service (this repo) | [sarli-s/AI-Services-Chat-and-Semantics](https://github.com/sarli-s/AI-Services-Chat-and-Semantics) | Python, FastAPI, OpenAI |

---

## Features

- **Chat endpoint** — Conversational assistant (Ori) that recommends products using GPT-4o
- **Semantic search endpoint** — Finds the most relevant products for a natural-language query using embeddings
- **Embedding cache** — Product embeddings are cached in memory via `/seed` to minimize API calls (~98% cost saving). The cache is empty after a restart until the next seed — the .NET backend seeds automatically on its startup and after every product change.

The assistant's persona and rules are in `SYSTEM_PROMPT` at the top of [chat_service.py](chat_service.py).

---

## Setup

Requires **Python 3.12** and an **OpenAI API key**.

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment variables
Copy [.env.example](.env.example) to `.env` and put your key in it:
```
OPENAI_API_KEY=<your_openai_api_key>
```
`.env` is git-ignored — never commit your key.

### 3. Run the service
```bash
python -m uvicorn chat_service:app --reload --port 8001
```
Use port **8001** — that's where the .NET backend looks for it. Interactive docs: `http://localhost:8001/docs`.

---

## Endpoints

### `POST /chat`
Chat with the AI gift assistant.

**Request:**
```json
{
  "message": "I need a gift for my dad",
  "history": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi! How can I help?" }
  ],
  "products": [
    { "id": "1", "name": "Custom Wooden Watch", "price": 89, "description": "...", "colors": ["Brown", "Black"], "inStock": true }
  ]
}
```

**Response:**
```json
{ "reply": "I'd love to help! ..." }
```

---

### `POST /seed`
Pre-cache product embeddings at startup. Call this once when your server starts, and again whenever the product catalog changes.

**Request:**
```json
{
  "products": [
    { "id": "1", "name": "Custom Wooden Watch", "description": "..." }
  ]
}
```

**Response:**
```json
{ "seeded": 1 }
```

---

### `POST /search`
Semantic search — returns products ranked by relevance to a natural-language query.

**Request:**
```json
{
  "query": "gift for someone who loves nature",
  "products": [...],
  "top_k": 5
}
```

**Response:**
```json
{
  "results": [
    { "id": "1", "name": "Custom Wooden Watch", "score": 0.91, ... }
  ]
}
```

---

## Integration Notes (for .NET server)

The [backend](https://github.com/sarli-s/APIproject) already does all of this (`SearchService` / `ChatService`):

1. On app startup → `POST /seed` with all products
2. On catalog change (add/update/delete) → `POST /seed` again
3. On user search → `POST /search`
4. Ensure JSON is serialized with **camelCase** property names

---

## Stopping the service
Press **Ctrl+C** in the terminal where it runs. If it was started in the background (Windows PowerShell):
```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess }
```
