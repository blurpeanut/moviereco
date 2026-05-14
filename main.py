from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx
import random

app = FastAPI(
    title="Movie Recommender — Vibe Check Edition",
    description="Answer 4 questions about your current vibe, get a movie recommendation powered by OMDb.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OMDB_API_KEY = "21cd354a"
OMDB_BASE_URL = "http://www.omdbapi.com/"

# ── Quiz definition ──────────────────────────────────────────────────────────

QUIZ = {
    "intro": "Welcome to the Vibe Check 🎬 Answer honestly. We judge a little.",
    "questions": [
        {
            "id": "mood",
            "question": "What's your current emotional state?",
            "options": {
                "a": "Need a good cry 😭",
                "b": "Ready to laugh till it hurts 😂",
                "c": "Edge of my seat, heart racing 😰",
                "d": "Warm & fuzzy, feeling soft 🥰",
            },
        },
        {
            "id": "setting",
            "question": "Pick a world to escape into tonight:",
            "options": {
                "a": "Galaxy far, far away 🚀",
                "b": "Rainy big city at night 🌆",
                "c": "Small cozy town with dark secrets 🏡",
                "d": "Historical epic or wild west 🤠",
            },
        },
        {
            "id": "energy",
            "question": "How much brain you bringing tonight?",
            "options": {
                "a": "None. Zero. Full potato mode 🥔",
                "b": "A little — I like a good story",
                "c": "100% — hit me with the plot twists 🧠",
                "d": "I want to FEEL things, not think",
            },
        },
        {
            "id": "company",
            "question": "Who's watching with you?",
            "options": {
                "a": "Just me and my snacks 🍿",
                "b": "Date night 💑",
                "c": "The whole squad 🎉",
                "d": "Family / kids in the mix 👨‍👩‍👧",
            },
        },
    ],
    "instructions": "POST your answers to /recommend — e.g. { \"mood\": \"b\", \"setting\": \"a\", \"energy\": \"c\", \"company\": \"a\" }",
}

# ── Recommendation map: (mood, setting) → candidate movie titles ─────────────

RECOMMENDATION_MAP: dict[tuple[str, str], list[str]] = {
    ("a", "a"): ["Interstellar", "Gravity", "Ad Astra"],
    ("a", "b"): ["Lost in Translation", "Her", "Collateral"],
    ("a", "c"): ["Eternal Sunshine of the Spotless Mind", "Manchester by the Sea", "The Lovely Bones"],
    ("a", "d"): ["Braveheart", "Gladiator", "The Last Samurai"],
    ("b", "a"): ["Guardians of the Galaxy", "Galaxy Quest", "The Hitchhiker's Guide to the Galaxy"],
    ("b", "b"): ["The Grand Budapest Hotel", "Crazy Stupid Love", "About Time"],
    ("b", "c"): ["Knives Out", "Hot Fuzz", "Clue"],
    ("b", "d"): ["Blazing Saddles", "Tombstone", "Butch Cassidy and the Sundance Kid"],
    ("c", "a"): ["Alien", "Event Horizon", "Life"],
    ("c", "b"): ["Se7en", "Nightcrawler", "Gone Girl"],
    ("c", "c"): ["The Gift", "Hereditary", "Midsommar"],
    ("c", "d"): ["No Country for Old Men", "There Will Be Blood", "True Grit"],
    ("d", "a"): ["The Martian", "Wall-E", "Arrival"],
    ("d", "b"): ["La La Land", "Before Sunrise", "Midnight in Paris"],
    ("d", "c"): ["Big Fish", "Little Miss Sunshine", "Chocolat"],
    ("d", "d"): ["The Princess Bride", "Cinema Paradiso", "Dances with Wolves"],
}

MOOD_LABELS = {
    "a": "cry-worthy",
    "b": "laugh-out-loud",
    "c": "edge-of-your-seat",
    "d": "heartwarming",
}

MOOD_PITCH = {
    "a": "Grab the tissues. This one is going to hit.",
    "b": "Get ready to ugly-laugh. We're not sorry.",
    "c": "Buckle up — this one will mess with your head in the best way.",
    "d": "Perfect for when you just want to feel something good.",
}

ENERGY_LABELS = {
    "a": "easy watch",
    "b": "solid story",
    "c": "mind-bender",
    "d": "emotional journey",
}

# ── Helpers ──────────────────────────────────────────────────────────────────


async def fetch_movie_by_title(title: str, year: Optional[str] = None) -> dict | None:
    params: dict = {"t": title, "apikey": OMDB_API_KEY, "plot": "full"}
    if year:
        params["y"] = year
    async with httpx.AsyncClient() as client:
        r = await client.get(OMDB_BASE_URL, params=params)
        data = r.json()
    return data if data.get("Response") == "True" else None


async def search_movies(query: str, page: int = 1) -> dict:
    params = {"s": query, "apikey": OMDB_API_KEY, "page": page}
    async with httpx.AsyncClient() as client:
        r = await client.get(OMDB_BASE_URL, params=params)
    return r.json()


def pick_candidate(candidates: list[str], energy: str, company: str) -> str:
    # Use energy + company letters as a deterministic but varied index
    offset = (ord(energy) - ord("a")) + (ord(company) - ord("a"))
    return candidates[offset % len(candidates)]


# ── Routes ───────────────────────────────────────────────────────────────────


@app.get("/", tags=["General"])
async def root():
    return {
        "message": "🎬 Movie Recommender — Vibe Check Edition",
        "how_to_use": [
            "1. GET  /quiz          → See the 4-question vibe check",
            "2. POST /recommend     → Submit answers, get your movie",
            "3. GET  /movie/{title} → Look up any movie directly",
            "4. GET  /search?q=...  → Search movies by keyword",
        ],
        "docs": "/docs",
    }


@app.get("/quiz", tags=["Quiz"])
async def get_quiz():
    """Return the Vibe Check quiz questions and answer options."""
    return QUIZ


class QuizAnswers(BaseModel):
    mood: str
    setting: str
    energy: str
    company: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "mood": "b",
                "setting": "c",
                "energy": "a",
                "company": "a",
            }
        }
    }


@app.post("/recommend", tags=["Recommend"])
async def recommend(answers: QuizAnswers):
    """
    Submit your Vibe Check answers (a/b/c/d for each question).
    Returns a tailored movie recommendation with full OMDb details.
    """
    valid = {"a", "b", "c", "d"}
    for field, val in answers.model_dump().items():
        if val not in valid:
            raise HTTPException(
                status_code=400,
                detail=f"'{field}' must be one of: a, b, c, d — got '{val}'",
            )

    candidates = RECOMMENDATION_MAP.get(
        (answers.mood, answers.setting),
        ["The Shawshank Redemption", "Forrest Gump", "The Truman Show"],
    )
    chosen_title = pick_candidate(candidates, answers.energy, answers.company)

    movie = await fetch_movie_by_title(chosen_title)
    if not movie:
        movie = await fetch_movie_by_title("The Shawshank Redemption")

    vibe_score = random.randint(87, 99)

    return {
        "vibe_check_result": {
            "mood": MOOD_LABELS.get(answers.mood, answers.mood),
            "energy": ENERGY_LABELS.get(answers.energy, answers.energy),
            "vibe_score": f"{vibe_score}% match ✨",
            "pitch": MOOD_PITCH.get(answers.mood, "We think you'll love this."),
        },
        "recommendation": {
            "title": movie.get("Title"),
            "year": movie.get("Year"),
            "genre": movie.get("Genre"),
            "director": movie.get("Director"),
            "actors": movie.get("Actors"),
            "plot": movie.get("Plot"),
            "imdb_rating": movie.get("imdbRating"),
            "runtime": movie.get("Runtime"),
            "rated": movie.get("Rated"),
            "poster": movie.get("Poster"),
            "imdb_id": movie.get("imdbID"),
        },
    }


@app.get("/movie/{title}", tags=["Movies"])
async def get_movie(title: str, year: Optional[str] = None):
    """Look up a specific movie by title. Optionally filter by year."""
    movie = await fetch_movie_by_title(title, year)
    if not movie:
        raise HTTPException(status_code=404, detail=f"No movie found for '{title}'")
    return movie


@app.get("/search", tags=["Movies"])
async def search(q: str, page: int = 1):
    """Search movies by keyword. Returns up to 10 results per page."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query param 'q' cannot be empty")
    data = await search_movies(q, page)
    if data.get("Response") == "False":
        raise HTTPException(status_code=404, detail=data.get("Error", "No results found"))
    return {
        "query": q,
        "page": page,
        "total_results": data.get("totalResults"),
        "results": data.get("Search", []),
    }
