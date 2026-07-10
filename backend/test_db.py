import os
import tempfile
from database import init_db, add_note, get_note_by_url, get_all_notes, get_next_review_note, delete_note, get_due_count

def test_database_flow():
    # Use a temporary file for the database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        print(f"Initializing test database at {db_path}...")
        init_db(db_path)
        
        note_id = "test-note-123"
        url = "https://example.com/test-article"
        title = "Test Article Title"
        content = "This is some test content for the personal knowledge vault Neko."
        tags = ["test", "knowledge", "neko"]
        embedding = [0.1, 0.2, 0.3, -0.4, 0.5] * 200 + [0.9, -0.9, 0.8, -0.8] # 1004 floats, let's make it 1024
        embedding += [0.0] * (1024 - len(embedding))
        
        print("Adding note...")
        success = add_note(db_path, note_id, url, title, content, tags, embedding)
        assert success, "Failed to add note"
        
        print("Retrieving note by URL...")
        note = get_note_by_url(db_path, url)
        assert note is not None, "Note was not retrieved"
        assert note["id"] == note_id, "Note ID mismatch"
        assert note["title"] == title, "Title mismatch"
        assert note["content"] == content, "Content mismatch"
        assert set(note["tags"]) == set(tags), f"Tags mismatch: {note['tags']} vs {tags}"
        assert len(note["embedding"]) == 1024, f"Embedding size mismatch, got {len(note['embedding'])}"
        
        print("Checking all notes retrieval...")
        all_notes = get_all_notes(db_path)
        assert len(all_notes) == 1, "Expected 1 note in database"
        assert all_notes[0]["id"] == note_id
        
        print("Checking spacing review fetching...")
        due_count = get_due_count(db_path)
        assert due_count == 1, f"Expected 1 due note, got {due_count}"
        
        review_note = get_next_review_note(db_path)
        assert review_note is not None
        assert review_note["id"] == note_id
        
        print("Deleting note...")
        success = delete_note(db_path, note_id)
        assert success, "Failed to delete note"
        
        note_after_delete = get_note_by_url(db_path, url)
        assert note_after_delete is None, "Note still exists after deletion"
        
        due_count_after = get_due_count(db_path)
        assert due_count_after == 0, f"Expected 0 due notes after deletion, got {due_count_after}"
        
        print("Database smoke test passed successfully!")
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    test_database_flow()
