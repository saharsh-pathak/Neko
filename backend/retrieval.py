import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from pylate import models
import os
import gc

class NekoRetriever:
    def __init__(self, db_path=None):
        self.db_path = db_path
        self.embedding_model = None
        self.colbert_model = None
        
    def _load_embedding_model(self):
        if self.embedding_model is None:
            print("Loading LFM2.5-Embedding-350M model...")
            # Load sentence transformer model. trust_remote_code=True is required for LFM2.5
            self.embedding_model = SentenceTransformer(
                "LiquidAI/LFM2.5-Embedding-350M", 
                trust_remote_code=True,
                device="cpu"  # Keep CPU-only by default for local/on-device stability
            )
            
    def _load_colbert_model(self):
        if self.colbert_model is None:
            print("Loading LFM2.5-ColBERT-350M model...")
            # Load PyLate ColBERT model
            self.colbert_model = models.ColBERT(
                model_name_or_path="LiquidAI/LFM2.5-ColBERT-350M",
                trust_remote_code=True,
                device="cpu"
            )
            # Standard ColBERT padding token fix
            if self.colbert_model.tokenizer.pad_token is None:
                self.colbert_model.tokenizer.pad_token = self.colbert_model.tokenizer.eos_token

    def get_embedding(self, text: str) -> list:
        """Generates a dense embedding for a document or query."""
        self._load_embedding_model()
        # Add the recommended prefix for document encoding
        formatted_text = f"document: {text}"
        embedding = self.embedding_model.encode(formatted_text, convert_to_numpy=True)
        return embedding.tolist()

    def get_query_embedding(self, query: str) -> list:
        """Generates a dense embedding for a search query."""
        self._load_embedding_model()
        # Add the recommended prefix for query encoding
        formatted_query = f"query: {query}"
        embedding = self.embedding_model.encode(formatted_query, convert_to_numpy=True)
        return embedding.tolist()

    def compute_cosine_similarity(self, query_emb: list, doc_embs: list) -> list:
        """Computes cosine similarity between query and list of document embeddings."""
        if not doc_embs:
            return []
        q = np.array(query_emb)
        docs = np.array(doc_embs)
        
        # Calculate dot products of normalized vectors
        q_norm = q / np.linalg.norm(q)
        docs_norms = np.linalg.norm(docs, axis=1, keepdims=True)
        # Handle zero divisions
        docs_norms[docs_norms == 0] = 1.0
        docs_norm = docs / docs_norms
        
        similarities = np.dot(docs_norm, q_norm)
        return similarities.tolist()

    def colbert_score(self, query_tokens_emb, doc_tokens_emb) -> float:
        """Computes the MaxSim score between query token embeddings and document token embeddings.
        
        query_tokens_emb: shape (L_q, D) - 2D numpy array
        doc_tokens_emb: shape (L_d, D) - 2D numpy array
        """
        # Compute cosine similarity matrix between query tokens and document tokens
        # Norms along the embedding dimension (axis 1)
        q_norms = np.linalg.norm(query_tokens_emb, axis=1, keepdims=True)
        d_norms = np.linalg.norm(doc_tokens_emb, axis=1, keepdims=True)
        q_norms[q_norms == 0] = 1.0
        d_norms[d_norms == 0] = 1.0
        
        q_normalized = query_tokens_emb / q_norms
        d_normalized = doc_tokens_emb / d_norms
        
        # Similarity matrix: (L_q, L_d)
        similarity_matrix = np.dot(q_normalized, d_normalized.T)
        
        # MaxSim: for each query token, take max similarity with any doc token, then sum
        max_sim = np.max(similarity_matrix, axis=1)
        return float(np.sum(max_sim))

    def retrieve_and_rerank(self, query: str, candidate_notes: list, top_k_dense: int = 15, top_m_rerank: int = 5) -> list:
        """Two-stage retrieval pipeline:
        1. Dense retrieval using LFM2.5-Embedding-350M (top_k_dense candidates)
        2. Late-interaction re-ranking using LFM2.5-ColBERT-350M (top_m_rerank final results)
        """
        if not candidate_notes:
            return []
            
        # --- Stage 1: Dense Retrieval ---
        query_emb = self.get_query_embedding(query)
        doc_embs = [note["embedding"] for note in candidate_notes if note["embedding"] is not None]
        valid_notes = [note for note in candidate_notes if note["embedding"] is not None]
        
        if not valid_notes:
            return []
            
        similarities = self.compute_cosine_similarity(query_emb, doc_embs)
        
        # Pair notes with their dense scores
        scored_notes = []
        for i, note in enumerate(valid_notes):
            scored_notes.append({
                "note": note,
                "dense_score": similarities[i]
            })
            
        # Sort by dense score descending and select top_k_dense
        scored_notes.sort(key=lambda x: x["dense_score"], reverse=True)
        candidates = scored_notes[:top_k_dense]
        
        if not candidates:
            return []
            
        # --- Stage 2: ColBERT Re-ranking ---
        self._load_colbert_model()
        
        # Extract plain texts
        candidate_texts = [cand["note"]["content"] for cand in candidates]
        
        # Encode query and candidates
        # pylate returns list of arrays
        query_encoded = self.colbert_model.encode([query], is_query=True, show_progress_bar=False)
        docs_encoded = self.colbert_model.encode(candidate_texts, is_query=False, show_progress_bar=False)
        
        q_emb = query_encoded[0] # Shape (L_q, D)
        
        final_results = []
        for i, cand in enumerate(candidates):
            d_emb = docs_encoded[i] # Shape (L_d, D)
            colbert_score_val = self.colbert_score(q_emb, d_emb)
            
            # Keep note details and scores
            note_data = cand["note"].copy()
            # Clean up raw embedding to keep response payload small
            if "embedding" in note_data:
                del note_data["embedding"]
                
            final_results.append({
                "note": note_data,
                "dense_score": cand["dense_score"],
                "colbert_score": colbert_score_val
            })
            
        # Sort by ColBERT score descending
        final_results.sort(key=lambda x: x["colbert_score"], reverse=True)
        
        # Free up GPU/CPU memory if needed
        gc.collect()
        
        return final_results[:top_m_rerank]
