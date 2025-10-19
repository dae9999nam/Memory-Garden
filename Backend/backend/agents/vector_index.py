import faiss
import numpy as np
from typing import Dict, List

class VectorIndex:
    def __init__(self, dimension: int):
        self.index = faiss.IndexFlatL2(dimension)   # L2 Euclidean distance search
        self.docs: List[Dict] = []
    
    def add(self, doc: Dict):
        """Adds a single doc with embedding"""
        vec = np.array([doc["embedding"]], dtype = "float32")
        self.index.add(vec)
        self.docs.append(doc)
    
    def add_batch(self, docs: List[Dict]):
        """Adds a batch of docs with embeddings"""
        vecs = np.array([d["embedding"] for d in docs], dtype = "float32")
        self.index.add(vecs)
        self.docs.extend(docs)
    
    def search(self, query_vec: List[float], k : int) -> List[Dict]:
        """Return top-k docs by semantic FAISS similarity"""
        query = np.array([query_vec], dtype = "float32")
        D, I = self.index.search(query, k)
        return [self.docs[i] for i in I[0] if i < len(self.docs)]