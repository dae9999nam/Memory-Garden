from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaEmbeddings
from typing import List

class EmbeddingModel:
    def __init__(self, backend: str, model : str):
        """
        EmbeddingModel wrapper

        backend engine: 
        - "ollama" (OllamaEmbeddings) : local, consistent with Ollama LLM 
        - "hf" (HuggingFace SentenceTransformers) : Fast, optimized for similarity
        """
        self.backend = backend
        if backend == "hf":
            self.model = SentenceTransformer(model = model)
        elif backend == "ollama":
            self.model = OllamaEmbeddings(model = model)
        else:
            raise ValueError("Backend must be 'ollama' or 'hf'")
    
    def embed(self, text: str) -> List[float]:
        """Embedding the text to embedding vectors"""
        if self.backend == "ollama":
            return self.model.embed_query(text)
        elif self.backend == "hf":
            return self.model.encode(text).tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self.backend == "ollama":
            return [self.model.embed_query(t) for t in texts]
        elif self.backend == "hf":
            return self.model.encode(texts).tolist()
        