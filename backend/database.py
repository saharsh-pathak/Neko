import sqlite3
import json
import os
import struct
from datetime import datetime, date

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "neko.db")

def get_db_connection(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(db_path=DEFAULT_DB_PATH):
    """Initializes the SQLite database tables."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Create notes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        url TEXT UNIQUE,
        title TEXT,
        content TEXT,
        embedding BLOB,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create tags table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        note_id TEXT,
        tag TEXT,
        PRIMARY KEY (note_id, tag),
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    )
    """)
    
    # Create reviews table (for SM-2 spaced repetition)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        note_id TEXT PRIMARY KEY,
        interval INTEGER DEFAULT 1,
        repetition INTEGER DEFAULT 0,
        ease_factor REAL DEFAULT 2.5,
        next_review_date TEXT,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    )
    """)
    
    # Create review_history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id TEXT,
        review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        rating INTEGER,
        FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

def float_list_to_blob(floats):
    """Converts a list of floats to a binary BLOB."""
    if not floats:
        return None
    return struct.pack(f"{len(floats)}f", *floats)

def blob_to_float_list(blob):
    """Converts a binary BLOB back to a list of floats."""
    if not blob:
        return []
    num_floats = len(blob) // 4
    return list(struct.unpack(f"{num_floats}f", blob))

def add_note(db_path, note_id, url, title, content, tags, embedding=None):
    """Adds a new note or replaces an existing one, sets up tags and reviews."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        # Convert embedding to BLOB
        embedding_blob = float_list_to_blob(embedding) if embedding else None
        
        # Insert or replace note
        cursor.execute(
            "INSERT OR REPLACE INTO notes (id, url, title, content, embedding, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (note_id, url, title, content, embedding_blob, datetime.utcnow().isoformat())
        )
        
        # Clean existing tags for this note
        cursor.execute("DELETE FROM tags WHERE note_id = ?", (note_id,))
        # Insert new tags
        for tag in tags:
            tag = tag.strip().lower()
            if tag:
                cursor.execute("INSERT OR IGNORE INTO tags (note_id, tag) VALUES (?, ?)", (note_id, tag))
                
        # Set up SM-2 initial state if not already existing
        cursor.execute("INSERT OR IGNORE INTO reviews (note_id, interval, repetition, ease_factor, next_review_date) VALUES (?, 1, 0, 2.5, ?)",
                       (note_id, date.today().isoformat()))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_note(db_path, note_id):
    """Deletes a note from the database."""
    conn = get_db_connection(db_path)
    try:
        conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_note_by_url(db_path, url):
    """Retrieves a single note and its tags by its URL."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    note_row = cursor.execute("SELECT * FROM notes WHERE url = ?", (url,)).fetchone()
    if not note_row:
        conn.close()
        return None
        
    note = dict(note_row)
    # Get tags
    tags_rows = cursor.execute("SELECT tag FROM tags WHERE note_id = ?", (note["id"],)).fetchall()
    note["tags"] = [row["tag"] for row in tags_rows]
    note["embedding"] = blob_to_float_list(note["embedding"])
    
    conn.close()
    return note

def get_all_notes(db_path):
    """Retrieves all notes and their tags."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    note_rows = cursor.execute("SELECT id, url, title, content, timestamp FROM notes ORDER BY timestamp DESC").fetchall()
    notes = []
    
    for row in note_rows:
        note = dict(row)
        tags_rows = cursor.execute("SELECT tag FROM tags WHERE note_id = ?", (note["id"],)).fetchall()
        note["tags"] = [r["tag"] for r in tags_rows]
        
        # Get review info if it exists
        review_row = cursor.execute("SELECT interval, repetition, ease_factor, next_review_date FROM reviews WHERE note_id = ?", (note["id"],)).fetchone()
        if review_row:
            note["review"] = dict(review_row)
        else:
            note["review"] = None
            
        notes.append(note)
        
    conn.close()
    return notes

def get_notes_for_retrieval(db_path):
    """Returns notes with their embeddings for similarity search."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    rows = cursor.execute("SELECT id, url, title, content, embedding FROM notes").fetchall()
    
    notes = []
    for row in rows:
        notes.append({
            "id": row["id"],
            "url": row["url"],
            "title": row["title"],
            "content": row["content"],
            "embedding": blob_to_float_list(row["embedding"])
        })
    conn.close()
    return notes

def get_all_tags(db_path):
    """Gets all unique tags stored in the database."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    rows = cursor.execute("SELECT DISTINCT tag FROM tags ORDER BY tag ASC").fetchall()
    conn.close()
    return [row["tag"] for row in rows]

def get_next_review_note(db_path):
    """Gets the next note scheduled for spaced repetition review."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    
    # Select notes that are due, ordering by the oldest due date
    row = cursor.execute("""
        SELECT n.id, n.url, n.title, n.content, r.interval, r.repetition, r.ease_factor, r.next_review_date
        FROM notes n
        JOIN reviews r ON n.id = r.note_id
        WHERE r.next_review_date <= ?
        ORDER BY r.next_review_date ASC
        LIMIT 1
    """, (today_str,)).fetchone()
    
    if not row:
        conn.close()
        return None
        
    note = dict(row)
    tags_rows = cursor.execute("SELECT tag FROM tags WHERE note_id = ?", (note["id"],)).fetchall()
    note["tags"] = [r["tag"] for r in tags_rows]
    
    conn.close()
    return note

def get_due_count(db_path):
    """Gets the number of items due for review today or overdue."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    row = cursor.execute("SELECT COUNT(*) as count FROM reviews WHERE next_review_date <= ?", (today_str,)).fetchone()
    count = row["count"] if row else 0
    conn.close()
    return count

def update_review_sm2(db_path, note_id, rating, next_interval, next_repetition, next_ease_factor, next_review_date):
    """Updates SM-2 params in reviews table and adds a row to review_history."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        # Update reviews table
        cursor.execute("""
            INSERT OR REPLACE INTO reviews (note_id, interval, repetition, ease_factor, next_review_date)
            VALUES (?, ?, ?, ?, ?)
        """, (note_id, next_interval, next_repetition, next_ease_factor, next_review_date))
        
        # Log to history
        cursor.execute("""
            INSERT INTO review_history (note_id, rating) VALUES (?, ?)
        """, (note_id, rating))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
