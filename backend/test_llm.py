import sys
from llm import is_ollama_running, generate_rag_response, generate_quiz_question, evaluate_quiz_answer

def test_llm_flow():
    print("Checking if Ollama is running...")
    running = is_ollama_running()
    print(f"Ollama running status: {running}")
    
    # Test fallback/offline behaviour or actual API calls
    test_note_content = (
        "Neko is a local, private knowledge vault that stores your bookmarks, web highlights, "
        "and notes on-device. It uses SQLite for storage and LFM2.5 models for fast vector search and ColBERT reranking."
    )
    test_title = "Neko Knowledge Vault Description"
    
    if running:
        print("\n1. Testing RAG response generation...")
        retrieved = [{
            "note": {"title": test_title, "url": "https://neko.local", "content": test_note_content},
            "colbert_score": 25.0
        }]
        rag_resp = generate_rag_response("What database does Neko use?", retrieved)
        print(f"RAG Response: {rag_resp}")
        assert "SQLite" in rag_resp or "sqlite" in rag_resp.lower(), "Expected RAG response to mention SQLite"
        
        print("\n2. Testing Quiz Question generation...")
        quiz = generate_quiz_question(test_title, test_note_content)
        print(f"Quiz Question: {quiz.get('question')}")
        print(f"Quiz Hint: {quiz.get('hint')}")
        assert "question" in quiz, "Expected 'question' in quiz result"
        
        print("\n3. Testing Quiz Answer evaluation...")
        evaluation = evaluate_quiz_answer(
            test_note_content, 
            quiz.get('question', "What database does Neko use?"), 
            "It uses SQLite database."
        )
        print(f"Evaluation Rating: {evaluation.get('rating')}")
        print(f"Evaluation Feedback: {evaluation.get('feedback')}")
        print(f"Correct Answer: {evaluation.get('correct_answer')}")
        assert 0 <= evaluation.get('rating', -1) <= 5, "Rating should be between 0 and 5"
        
        print("\nOllama integration test passed successfully!")
    else:
        print("\nOllama is not running. Testing offline/fallback response...")
        retrieved = []
        rag_resp = generate_rag_response("What database does Neko use?", retrieved)
        print(f"RAG Response (Offline): {rag_resp}")
        assert "no relevant notes" in rag_resp.lower() or "ollama is not running" in rag_resp.lower()
        
        quiz = generate_quiz_question(test_title, test_note_content)
        print(f"Quiz Question (Offline): {quiz.get('question')}")
        assert "question" in quiz
        
        evaluation = evaluate_quiz_answer(test_note_content, "What database does Neko use?", "It uses SQLite.")
        print(f"Evaluation (Offline): {evaluation}")
        assert evaluation.get("rating") == 3
        print("\nOffline fallback test passed successfully!")

if __name__ == "__main__":
    test_llm_flow()
