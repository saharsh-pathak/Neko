import os
import tempfile
import numpy as np
from database import init_db, add_note, get_notes_for_retrieval
from retrieval import NekoRetriever

def test_retrieval_flow():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        init_db(db_path)
        retriever = NekoRetriever(db_path=db_path)
        
        # Test documents
        doc1 = "Artificial intelligence and machine learning are transforming modern software development by automating complex programming tasks."
        doc2 = "Cooking the perfect Italian pasta requires high quality durum wheat semolina, boiling water, salt, and precise cooking times."
        doc3 = "Deep learning models, specifically transformers, have achieved state-of-the-art results in natural language processing and computer vision."
        
        print("1. Generating embeddings for documents...")
        emb1 = retriever.get_embedding(doc1)
        emb2 = retriever.get_embedding(doc2)
        emb3 = retriever.get_embedding(doc3)
        
        assert len(emb1) == 1024, f"Expected 1024 dimensions, got {len(emb1)}"
        print("Embeddings generated successfully. Dimension count:", len(emb1))
        
        # Add to database
        add_note(db_path, "doc1", "https://ai-blog.com/ml", "AI & ML in Software", doc1, ["ai", "programming"], emb1)
        add_note(db_path, "doc2", "https://cooking.com/pasta", "How to cook Pasta", doc2, ["cooking", "recipe"], emb2)
        add_note(db_path, "doc3", "https://ai-blog.com/transformers", "Deep Learning & Transformers", doc3, ["ai", "deep-learning"], emb3)
        
        # Retrieve candidate notes
        candidates = get_notes_for_retrieval(db_path)
        assert len(candidates) == 3, f"Expected 3 candidates, got {len(candidates)}"
        
        # Test search query
        query = "How do deep neural networks and transformer architectures improve computer vision and language tasks?"
        print(f"\n2. Searching for query: '{query}'")
        
        results = retriever.retrieve_and_rerank(query, candidates, top_k_dense=3, top_m_rerank=2)
        
        print("\nSearch results (re-ranked by ColBERT):")
        for i, res in enumerate(results):
            note = res["note"]
            print(f"Rank {i+1}: {note['title']}")
            print(f"  URL: {note['url']}")
            print(f"  Dense Score: {res['dense_score']:.4f}")
            print(f"  ColBERT Score: {res['colbert_score']:.4f}")
            print(f"  Snippet: {note['content'][:60]}...")
            
        assert len(results) > 0, "No search results returned"
        # The first result should be doc3 (explicitly about deep learning/transformers) or doc1
        best_title = results[0]["note"]["title"]
        assert "Pasta" not in best_title, "Reranker ranked Pasta above AI/Transformers!"
        print("\nRetrieval and Re-ranking smoke test passed successfully!")
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    test_retrieval_flow()
