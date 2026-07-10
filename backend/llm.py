import requests
import json
import os
import re

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

def get_available_model():
    """Gets the first available Ollama model, prioritising qwen3:4b or what is installed."""
    default_model = os.environ.get("OLLAMA_MODEL", "qwen3:4b")
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            installed_models = [m.get("name") for m in models_data if m.get("name")]
            if not installed_models:
                return default_model
            # Prioritise qwen3:4b
            if default_model in installed_models:
                return default_model
            # Prioritise standard models like llama3.2:1b
            for m in installed_models:
                if "llama3.2:1b" in m:
                    return m
            # If not, take the first installed model
            return installed_models[0]
    except Exception:
        pass
    return default_model

OLLAMA_MODEL = get_available_model()
print(f"Ollama integration selected model: {OLLAMA_MODEL}")

def is_ollama_running():
    """Checks if Ollama is running and accessible."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def generate_rag_response(query: str, retrieved_notes: list) -> str:
    """Synthesizes an answer to a query using the context from retrieved notes."""
    if not is_ollama_running():
        return "Error: Ollama is not running. Please start Ollama locally to enable RAG."
        
    if not retrieved_notes:
        return "No relevant notes were found in your vault to answer this question."

    # Build context from notes
    context_items = []
    for i, res in enumerate(retrieved_notes):
        note = res["note"]
        score = res.get("colbert_score", res.get("dense_score", 0))
        context_items.append(
            f"Source [{i+1}]: {note['title']} ({note['url']})\n"
            f"Content: {note['content']}\n"
            f"Relevance Score: {score:.2f}"
        )
    context_str = "\n\n".join(context_items)

    system_prompt = (
        "You are Neko, a personal, private knowledge assistant. You answer questions based ONLY on the "
        "provided context from the user's saved notes. If the answer cannot be found in the context, "
        "say so clearly. Do not make up information outside of the context. Maintain a professional, "
        "helpful, and concise tone."
    )
    
    user_content = (
        f"Context from my saved vault notes:\n"
        f"---------------------\n"
        f"{context_str}\n"
        f"---------------------\n\n"
        f"Question: {query}\n\n"
        f"Answer:"
    )

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "stream": False
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["message"]["content"]
        else:
            return f"Error: Ollama returned status code {response.status_code}."
    except Exception as e:
        return f"Error connecting to Ollama: {str(e)}"

def generate_quiz_question(note_title: str, note_content: str) -> dict:
    """Generates an active recall quiz question based on a note's content."""
    if not is_ollama_running():
        return {
            "error": "Ollama is not running. Start Ollama to generate quizzes.",
            "question": "Ollama offline. Please start Ollama."
        }
        
    system_prompt = (
        "You are an expert educator. Given a note's title and content, generate a single, direct "
        "short-answer question that tests the user's conceptual understanding or recall of key facts in the note. "
        "The question must be answerable in 1-2 sentences. Avoid multiple-choice or true/false formats. "
        "Return your response in JSON format with two keys:\n"
        "1. 'question': The question text.\n"
        "2. 'hint': A subtle hint to help the user if they struggle."
    )
    
    user_content = (
        f"Note Title: {note_title}\n"
        f"Note Content: {note_content}\n"
    )

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "format": "json",  # Ask Ollama for JSON structure
                "stream": False
            },
            timeout=30
        )
        if response.status_code == 200:
            data = json.loads(response.json()["message"]["content"])
            return {
                "question": data.get("question", "Could not generate question."),
                "hint": data.get("hint", "No hint available.")
            }
        else:
            return {"error": f"Ollama error: {response.status_code}", "question": "Failed to generate question."}
    except Exception as e:
        # Fallback if JSON format fails or other error
        return {
            "question": f"What are the key takeaways from the note: '{note_title}'?",
            "hint": "Recall the main points mentioned in the note."
        }

def evaluate_quiz_answer(note_content: str, question: str, user_answer: str) -> dict:
    """Evaluates the user's quiz answer and computes an SM-2 rating (0-5) and feedback."""
    if not is_ollama_running():
        return {
            "rating": 3,
            "feedback": "Ollama offline. Defaulting score to 3.",
            "correct_answer": "Check your saved note contents directly."
        }

    system_prompt = (
        "You are an objective grader. Evaluate the user's answer to the question based on the note content.\n"
        "Assign a score from 0 to 5 based on the SM-2 scale:\n"
        "5 - Perfect response. Completely accurate and comprehensive.\n"
        "4 - Correct response after a hesitation / minor detail missing, but essentially correct.\n"
        "3 - Correct response, but with serious difficulty (missing key concepts, partially correct).\n"
        "2 - Incorrect response, but the correct one was easy to recall (shows some familiarity).\n"
        "1 - Incorrect response, completely missed the point.\n"
        "0 - Complete blackout or empty answer.\n\n"
        "Provide your evaluation in JSON format with three keys:\n"
        "1. 'rating': The integer score (0-5).\n"
        "2. 'feedback': A brief, constructive sentence explaining the grade.\n"
        "3. 'correct_answer': The actual correct answer or key points from the note."
    )

    user_content = (
        f"Note Content: {note_content}\n"
        f"Question: {question}\n"
        f"User Answer: {user_answer}\n"
    )

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "format": "json",
                "stream": False
            },
            timeout=30
        )
        if response.status_code == 200:
            data = json.loads(response.json()["message"]["content"])
            # Ensure rating is an integer between 0 and 5
            rating = int(data.get("rating", 3))
            rating = max(0, min(5, rating))
            return {
                "rating": rating,
                "feedback": data.get("feedback", "No feedback provided."),
                "correct_answer": data.get("correct_answer", "No reference answer provided.")
            }
        else:
            return {
                "rating": 3,
                "feedback": f"Failed to grade (status {response.status_code}).",
                "correct_answer": "Refer to the source note."
            }
    except Exception as e:
        return {
            "rating": 3,
            "feedback": f"Error during grading: {str(e)}",
            "correct_answer": "Refer to the source note."
        }
