import os
import hashlib
import math
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

import database as db
from retrieval import NekoRetriever
import llm

# Create FastAPI app
app = FastAPI(
    title="Neko API",
    description="Local backend API for Neko - Your Personal, Private Knowledge Vault"
)

# Enable CORS for Chrome Extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Retriever
retriever = NekoRetriever(db_path=db.DEFAULT_DB_PATH)

# Initialize database tables on startup
@app.on_event("startup")
def startup_event():
    db.init_db()

# Pydantic Schemas
class NoteCreate(BaseModel):
    url: str
    title: str
    content: str
    tags: List[str] = []

class SearchRequest(BaseModel):
    query: str
    top_k: int = 15
    top_m: int = 5

class QuizSubmit(BaseModel):
    note_id: str
    question: str
    user_answer: str

# API Endpoints

@app.post("/api/notes")
def create_note(note: NoteCreate):
    """Saves a note, generates dense embeddings, and sets up SM-2 spaced repetition."""
    try:
        # Generate stable note ID using md5 hash of URL
        note_id = hashlib.md5(note.url.encode('utf-8')).hexdigest()
        
        # Generate dense embedding
        print(f"Generating embedding for note: {note.title}...")
        embedding = retriever.get_embedding(note.content)
        
        # Save to database
        db.add_note(
            db_path=db.DEFAULT_DB_PATH,
            note_id=note_id,
            url=note.url,
            title=note.title,
            content=note.content,
            tags=note.tags,
            embedding=embedding
        )
        return {"status": "success", "note_id": note_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save note: {str(e)}")

@app.get("/api/notes")
def list_notes():
    """Returns all saved notes with tags (without raw embeddings)."""
    try:
        notes = db.get_all_notes(db.DEFAULT_DB_PATH)
        return notes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/notes/{note_id}")
def delete_note(note_id: str):
    """Deletes a note from the vault."""
    try:
        db.delete_note(db.DEFAULT_DB_PATH, note_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tags")
def list_tags():
    """Returns all unique tags in the vault."""
    try:
        tags = db.get_all_tags(db.DEFAULT_DB_PATH)
        return tags
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
def search_vault(req: SearchRequest):
    """RAG-based search across the vault using 2-stage retrieval."""
    try:
        # Get candidates
        candidates = db.get_notes_for_retrieval(db.DEFAULT_DB_PATH)
        if not candidates:
            return {
                "answer": "Your vault is empty! Start saving bookmarks or highlights via the Neko extension.",
                "results": []
            }
            
        # Retrieve & rerank
        results = retriever.retrieve_and_rerank(
            query=req.query,
            candidate_notes=candidates,
            top_k_dense=req.top_k,
            top_m_rerank=req.top_m
        )
        
        # Generate RAG response
        answer = llm.generate_rag_response(req.query, results)
        
        return {
            "answer": answer,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/api/quiz/next")
def get_next_quiz():
    """Returns the next due quiz card and the total count of due reviews."""
    try:
        due_count = db.get_due_count(db.DEFAULT_DB_PATH)
        next_note = db.get_next_review_note(db.DEFAULT_DB_PATH)
        
        if not next_note:
            return {"note": None, "due_count": due_count}
            
        return {
            "note": {
                "id": next_note["id"],
                "url": next_note["url"],
                "title": next_note["title"],
                "tags": next_note["tags"]
            },
            "due_count": due_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quiz/generate")
def generate_quiz(payload: dict = Body(...)):
    """Generates an LLM question for a specific note."""
    note_id = payload.get("note_id")
    if not note_id:
        raise HTTPException(status_code=400, detail="Missing note_id")
        
    # Fetch note content
    conn = db.get_db_connection(db.DEFAULT_DB_PATH)
    row = conn.execute("SELECT title, content FROM notes WHERE id = ?", (note_id,)).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Note not found")
        
    question_data = llm.generate_quiz_question(row["title"], row["content"])
    return question_data

@app.post("/api/quiz/submit")
def submit_quiz(submit: QuizSubmit):
    """Evaluates the user's answer and updates the SM-2 spaced repetition state."""
    try:
        # Fetch current SM-2 state & content
        conn = db.get_db_connection(db.DEFAULT_DB_PATH)
        note_row = conn.execute("SELECT title, content FROM notes WHERE id = ?", (submit.note_id,)).fetchone()
        review_row = conn.execute("SELECT interval, repetition, ease_factor FROM reviews WHERE note_id = ?", (submit.note_id,)).fetchone()
        conn.close()
        
        if not note_row:
            raise HTTPException(status_code=404, detail="Note not found")
            
        # Grade user answer via LLM
        eval_data = llm.evaluate_quiz_answer(note_row["content"], submit.question, submit.user_answer)
        rating = eval_data["rating"]
        
        # Get prior SM-2 values
        prev_interval = review_row["interval"] if review_row else 1
        prev_repetition = review_row["repetition"] if review_row else 0
        prev_ease_factor = review_row["ease_factor"] if review_row else 2.5
        
        # Calculate next SM-2 interval
        if rating >= 3: # Correct/Pass
            if prev_repetition == 0:
                next_interval = 1
            elif prev_repetition == 1:
                next_interval = 6
            else:
                next_interval = math.ceil(prev_interval * prev_ease_factor)
            next_repetition = prev_repetition + 1
        else: # Incorrect/Fail
            next_interval = 1
            next_repetition = 0
            
        # Adjust ease factor
        next_ease_factor = prev_ease_factor + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
        if next_ease_factor < 1.3:
            next_ease_factor = 1.3
            
        next_review_date = (date.today() + timedelta(days=next_interval)).isoformat()
        
        # Save new state
        db.update_review_sm2(
            db_path=db.DEFAULT_DB_PATH,
            note_id=submit.note_id,
            rating=rating,
            next_interval=next_interval,
            next_repetition=next_repetition,
            next_ease_factor=next_ease_factor,
            next_review_date=next_review_date
        )
        
        return {
            "evaluation": eval_data,
            "sm2": {
                "interval": next_interval,
                "repetition": next_repetition,
                "ease_factor": next_ease_factor,
                "next_review_date": next_review_date
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Setup Static Files serving for Web UI Dashboard
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Mount static files (will hold style.css, app.js, images, etc.)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    """Serves the main dashboard HTML file."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "message": "Neko Backend is running!",
        "dashboard": "Place index.html under backend/static/ to view dashboard."
    }
