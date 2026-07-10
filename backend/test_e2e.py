import os
import sys
import time
import threading
import requests
import uvicorn

# Change directory to backend so uvicorn can find main:app and database.py
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def run_server():
    try:
        # Load main.py and run uvicorn
        import main
        uvicorn.run(main.app, host="127.0.0.1", port=8000, log_level="warning")
    except Exception as e:
        print(f"Server thread error: {e}", file=sys.stderr)

def run_e2e_tests():
    print("Starting FastAPI Uvicorn server in a daemon thread...")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    base_url = "http://127.0.0.1:8000"
    
    # Poll server until active (up to 60 seconds)
    print("Waiting for backend server to start (up to 60s)...")
    connected = False
    for i in range(1, 61):
        try:
            r = requests.get(f"{base_url}/", timeout=1)
            if r.status_code == 200:
                connected = True
                print(f"Server is up and running after {i} seconds!")
                break
        except requests.exceptions.RequestException:
            pass
        print(f"Waiting... ({i}s)")
        time.sleep(1)
        
    assert connected, "Backend server failed to start within 60 seconds."
    
    try:
        # Check server health
        print("Checking server root...")
        r = requests.get(f"{base_url}/")
        print(f"Root response status: {r.status_code}")
        assert r.status_code == 200, "Server is not responding"
        assert "<!DOCTYPE html>" in r.text or "Neko" in r.text, "Root page did not return dashboard HTML"

        # Create note
        print("\nSaving test bookmark...")
        note_data = {
            "url": "https://neko-test.com/about",
            "title": "Neko On-Device AI Vault",
            "content": "Neko runs fully locally. It uses Whisper for voice notes, SQLite for the DB, LFM2.5 for search, and Qwen3 for RAG.",
            "tags": ["neko", "ai", "local"]
        }
        r = requests.post(f"{base_url}/api/notes", json=note_data)
        print(f"Save note response: {r.status_code} - {r.json()}")
        assert r.status_code == 200
        note_id = r.json()["note_id"]
        
        # List notes
        print("\nListing notes...")
        r = requests.get(f"{base_url}/api/notes")
        print(f"Notes in database: {len(r.json())}")
        assert len(r.json()) >= 1
        
        # Test Search & RAG
        print("\nPerforming RAG search...")
        search_data = {
            "query": "Which models does Neko use?",
            "top_k": 2,
            "top_m": 1
        }
        r = requests.post(f"{base_url}/api/search", json=search_data)
        print(f"Search status: {r.status_code}")
        search_res = r.json()
        print(f"AI Synthesis:\n{search_res['answer']}\n")
        assert "LFM2.5" in search_res["answer"] or "Qwen3" in search_res["answer"] or "Whisper" in search_res["answer"] or "local" in search_res["answer"].lower()
        
        # Test Spaced Repetition Quiz Flow
        print("\nFetching next quiz card...")
        r = requests.get(f"{base_url}/api/quiz/next")
        print(f"Next quiz: {r.json()}")
        assert r.json()["note"] is not None
        assert r.json()["note"]["id"] == note_id
        
        print("\nGenerating LLM Quiz Question...")
        r = requests.post(f"{base_url}/api/quiz/generate", json={"note_id": note_id})
        question_data = r.json()
        print(f"Question: {question_data.get('question')}")
        print(f"Hint: {question_data.get('hint')}")
        assert "question" in question_data
        
        print("\nSubmitting answer to quiz...")
        submit_data = {
            "note_id": note_id,
            "question": question_data["question"],
            "user_answer": "It runs locally using Whisper, LFM2.5, SQLite, and Qwen3."
        }
        r = requests.post(f"{base_url}/api/quiz/submit", json=submit_data)
        submit_res = r.json()
        print(f"Grading Score: {submit_res['evaluation']['rating']}/5")
        print(f"Grading Feedback: {submit_res['evaluation']['feedback']}")
        assert 0 <= submit_res['evaluation']['rating'] <= 5
        
        print("\nCleaning up (Deleting test note)...")
        r = requests.delete(f"{base_url}/api/notes/{note_id}")
        assert r.status_code == 200
        
        print("\nAll integration checks passed successfully!")
        
    except Exception as e:
        print(f"E2E Test Failed: {str(e)}")
        raise e
    finally:
        print("Test complete. Daemon thread will close automatically.")

if __name__ == "__main__":
    run_e2e_tests()
