# Gift Store AI Service

A FastAPI-based AI microservice for an online personalized gift store.  
Provides a conversational chat assistant and semantic product search, powered by OpenAI.

---

## Features

- **Chat endpoint** — Conversational assistant (Ori) that recommends products using GPT-4o
- **Semantic search endpoint** — Finds the most relevant products for a natural-language query using embeddings
- **Embedding cache** — Product embeddings are cached at startup to minimize API calls (~98% cost saving)

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment variables
Create a `.env` file in the project root:
```
OPENAI_API_KEY=<your_openai_api_key>
STORE_NAME=<your_store_name>
STORE_DESCRIPTION=<your_store_description>
```

### 3. Run the service
```bash
uvicorn chat_service:app --reload --port 8001
```

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

1. On app startup → `POST /seed` with all products
2. On catalog change (add/update/delete) → `POST /seed` again
3. On user search → `POST /search`
4. Ensure JSON is serialized with **camelCase** property names
