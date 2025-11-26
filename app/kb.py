# app/kb.py
import os
import chromadb

# Optional local embedding model
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

class KB:
    def __init__(self, chroma_dir="chromadb_store"):
        # Use default chromadb client to avoid Settings/migration warnings
        self.client = chromadb.Client()

        # Ensure collection exists (works across different chroma versions)
        try:
            self.col = self.client.get_or_create_collection("qa_agent")
        except Exception:
            try:
                self.col = self.client.create_collection(name="qa_agent")
            except Exception as e:
                raise RuntimeError("Failed to get or create Chroma collection: " + str(e))

        # Try to load a local sentence-transformers model (optional)
        if SentenceTransformer is not None:
            try:
                self.embed_model = SentenceTransformer(EMBED_MODEL_NAME)
            except Exception as e:
                print("KB: could not load sentence-transformers model:", e)
                self.embed_model = None
        else:
            self.embed_model = None

    def query(self, query_text, n_results=5):
        """
        Query the Chroma collection and normalize responses across Chroma versions.
        Returns a list of dicts: {document, metadata, distance}
        """
        try:
            res = self.col.query(query_texts=[query_text], n_results=n_results, include=['documents', 'metadatas', 'distances'])
        except TypeError:
            # fallback API shape
            res = self.col.query(query_text, n_results=n_results)
        except Exception as e:
            # If any other exception occurs, raise it to caller
            raise

        hits = []

        # Normalize possible return shapes
        docs = []
        metads = []
        dists = []

        if isinstance(res, dict):
            docs = res.get('documents', [])
            metads = res.get('metadatas', [])
            dists = res.get('distances', [])
        elif isinstance(res, list):
            # older/newer responses could be lists of lists
            docs = res[0] if len(res) > 0 else []
            metads = res[1] if len(res) > 1 else []
            dists = res[2] if len(res) > 2 else []
        else:
            # Unexpected shape
            docs = res

        # Flatten lists if nested (e.g., [[doc1, doc2]])
        if isinstance(docs, list) and len(docs) > 0 and isinstance(docs[0], list):
            docs = docs[0]
        if isinstance(metads, list) and len(metads) > 0 and isinstance(metads[0], list):
            metads = metads[0]
        if isinstance(dists, list) and len(dists) > 0 and isinstance(dists[0], list):
            dists = dists[0]

        # Build normalized hits
        for i, doc in enumerate(docs):
            meta = metads[i] if i < len(metads) else {}
            dist = dists[i] if i < len(dists) else None
            hits.append({"document": doc, "metadata": meta, "distance": dist})

        return hits
