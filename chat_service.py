from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os, json
import numpy as np

load_dotenv()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'],
                   allow_methods=['*'], allow_headers=['*'])
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Cache: product_id -> embedding (populated via /seed at startup)
product_embeddings: dict[str, list[float]] = {}

# ── SYSTEM PROMPT ────────────────────────────────────────────
# This is the agent's persona. Edit this — not the code below.
SYSTEM_PROMPT = SYSTEM_PROMPT = """
You are Ori, a creative and warm gift assistant for an online personalized gift store.
Your goal is to help customers find the perfect gift and guide them through the personalization options.

Rules you must ALWAYS follow:
1. Always maintain a warm, enthusiastic, and helpful tone.
2. For every gift recommendation, explicitly ask or remind the customer that they can choose a custom engraving (text to engrave) and select their preferred color.
3. Keep answers to 3-4 sentences maximum to stay concise.
4. Always end your response with one clear follow-up question to help narrow down the choice (e.g., asking about the recipient, the budget, or the occasion).

Example:
User: I need a gift for my friend's birthday.
Assistant: I would love to help you find something special! A popular option is our Personalized Leather Journal ($45) or the Custom Wooden Watch ($89) — both can be beautifully engraved with his name or a special date, and come in various colors. What is your friend's style, and what budget do you have in mind?
"""

class Message(BaseModel):
    role: str      # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
    products: list = []    # will be filled in Hours 5-6

# ── CHAT ENDPOINT ────────────────────────────────────────────
@app.post('/chat')
async def chat(req: ChatRequest):
    # Build a product catalog string from the list .NET sent
    if req.products:
        catalog_lines = []
        for p in req.products:
            stock = 'in stock' #if p.get('inStock') else 'out of stock'
            colors = ', '.join(p['colors']) if p.get('colors') else 'N/A'
            line = f"- {p['name']} (${p['price']}) [{stock}] | Colors: {colors}: {p.get('description', '')}"
            catalog_lines.append(line)
        catalog = '\n'.join(catalog_lines)
        full_prompt = SYSTEM_PROMPT + f'\n\nAvailable products:\n{catalog}\n\nOnly recommend products from this list.'
    else:
        full_prompt = SYSTEM_PROMPT

    # Build conversation
    messages = [{'role': 'system', 'content': full_prompt}]
    for m in req.history:
        messages.append({'role': m.role, 'content': m.content})
    messages.append({'role': 'user', 'content': req.message})

    response = client.chat.completions.create(
        model='gpt-4o',
        messages=messages,
        max_tokens=400,
        temperature=0.5
    )
    return {'reply': response.choices[0].message.content}


# ── EMBEDDING FUNCTIONS ──────────────────────────────────────
def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model='text-embedding-3-small',
        input=text
    )
    return response.data[0].embedding

def cosine_similarity(a: list, b: list) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ── SEED ENDPOINT (call once at startup to cache product embeddings) ──
class SeedRequest(BaseModel):
    products: list

@app.post('/seed')
async def seed(req: SeedRequest):
    global product_embeddings
    new_cache = {}
    for p in req.products:
        pid = str(p.get('id') or p.get('name'))
        # Reuse existing embedding if already cached, otherwise compute
        new_cache[pid] = product_embeddings.get(pid) or get_embedding(
            f"{p.get('name', '')} {p.get('description', '')}"
        )
    product_embeddings = new_cache  # replaces old cache, deleted products are dropped
    return {'seeded': len(product_embeddings)}


# ── SEARCH ENDPOINT ──────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str
    products: list
    top_k: int = 5

@app.post('/search')
async def search(req: SearchRequest):
    if not req.products:
        return {'results': []}

    query_embedding = get_embedding(req.query)

    scored = []
    for p in req.products:
        pid = str(p.get('id') or p.get('name'))
        # Use cached embedding if available, otherwise compute and cache
        if pid not in product_embeddings:
            text = f"{p.get('name', '')} {p.get('description', '')}"
            product_embeddings[pid] = get_embedding(text)
        score = cosine_similarity(query_embedding, product_embeddings[pid])
        scored.append({**p, 'score': round(score, 3)})

    results = sorted(scored, key=lambda x: x['score'], reverse=True)
    return {'results': results[:req.top_k]}
