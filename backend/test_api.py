from fastapi.testclient import TestClient
import os
import shutil
import tempfile
import pytest

import database as db
from main import app

# Set a temp database path for testing
test_db_dir = tempfile.mkdtemp()
test_db_path = os.path.join(test_db_dir, "test_neko.db")
db.DEFAULT_DB_PATH = test_db_path

client = TestClient(app)

def test_endpoints():
    # 1. Init DB
    db.init_db(test_db_path)
    
    # 2. Test create note
    note_data = {
        "url": "https://neko-project.io/intro",
        "title": "Introduction to Neko Project",
        "content": "Neko is an offline-first private knowledge manager. It helps you remember what you read using active recall.",
        "tags": ["neko", "offline", "active-recall"]
    }
    
    print("Testing POST /api/notes...")
    response = client.post("/api/notes", json=note_data)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    note_id = res_data["note_id"]
    assert note_id is not None
    
    # 3. Test list notes
    print("Testing GET /api/notes...")
    response = client.get("/api/notes")
    assert response.status_code == 200
    notes = response.json()
    assert len(notes) == 1
    assert notes[0]["id"] == note_id
    assert set(notes[0]["tags"]) == set(note_data["tags"])
    
    # 4. Test list tags
    print("Testing GET /api/tags...")
    response = client.get("/api/tags")
    assert response.status_code == 200
    tags = response.json()
    assert set(tags) == set(note_data["tags"])
    
    # 5. Test search
    print("Testing POST /api/search...")
    search_data = {
        "query": "What is Neko?",
        "top_k": 2,
        "top_m": 1
    }
    response = client.post("/api/search", json=search_data)
    assert response.status_code == 200
    search_res = response.json()
    assert "answer" in search_res
    assert len(search_res["results"]) > 0
    assert search_res["results"][0]["note"]["id"] == note_id
    
    # 6. Test quiz next
    print("Testing GET /api/quiz/next...")
    response = client.get("/api/quiz/next")
    assert response.status_code == 200
    quiz_next = response.json()
    assert quiz_next["note"] is not None
    assert quiz_next["note"]["id"] == note_id
    assert quiz_next["due_count"] == 1
    
    # 7. Test quiz generate
    print("Testing POST /api/quiz/generate...")
    response = client.post("/api/quiz/generate", json={"note_id": note_id})
    assert response.status_code == 200
    quiz_data = response.json()
    assert "question" in quiz_data
    question = quiz_data["question"]
    
    # 8. Test quiz submit
    print("Testing POST /api/quiz/submit...")
    submit_data = {
        "note_id": note_id,
        "question": question,
        "user_answer": "It is an offline-first private knowledge manager that uses active recall."
    }
    response = client.post("/api/quiz/submit", json=submit_data)
    assert response.status_code == 200
    submit_res = response.json()
    assert "evaluation" in submit_res
    assert "rating" in submit_res["evaluation"]
    assert "sm2" in submit_res
    
    # 9. Test delete note
    print("Testing DELETE /api/notes/{note_id}...")
    response = client.delete(f"/api/notes/{note_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify empty list
    response = client.get("/api/notes")
    assert len(response.json()) == 0
    
    print("All endpoints tested successfully!")

if __name__ == "__main__":
    try:
        test_endpoints()
    finally:
        shutil.rmtree(test_db_dir, ignore_errors=True)
