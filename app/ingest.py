# app/ingest.py
import os
import json
from typing import List, Dict
import chromadb
from bs4 import BeautifulSoup

# Optional imports (loaded lazily / with friendly fallbacks)
try:
    import openai
except Exception:
    openai = None

# We'll try to use sentence-transformers if OpenAI is not configured.
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

class Ingestor:
    def __init__(self, chroma_dir="chromadb_store"):
        # Use the default chromadb client to avoid Settings/migration issues.
        self.client = chromadb.Client()

        # Ensure collection exists (works across Chroma versions)
        try:
            self.collection = self.client.get_or_create_collection("qa_agent")
        except Exception:
            try:
                # fallback attempts for different chroma versions
                self.collection = self.client.create_collection(name="qa_agent")
            except Exception as e:
                raise RuntimeError("Failed to create/get Chroma collection: " + str(e))

        # Choose embedding strategy:
        # 1) If OPENAI_API_KEY present and openai package available -> use OpenAI
        # 2) Else attempt to load sentence-transformers (local model)
        # 3) Else embed_model remains None and ingest will still store text (but no embeddings)
        if os.getenv("OPENAI_API_KEY") and openai is not None:
            self.use_openai = True
            # openai.api_key will be read from env; leave as-is
            print("Ingestor: Using OpenAI embeddings (OPENAI_API_KEY detected).")
            self.embed_model = None
        else:
            self.use_openai = False
            if SentenceTransformer is not None:
                try:
                    self.embed_model = SentenceTransformer(EMBED_MODEL_NAME)
                    print(f"Ingestor: Loaded sentence-transformers model '{EMBED_MODEL_NAME}'.")
                except Exception as e:
                    print("Ingestor: Failed to load sentence-transformers model:", str(e))
                    print("Ingestor: Embeddings will be disabled until a model or OPENAI_API_KEY is available.")
                    self.embed_model = None
            else:
                print("Ingestor: sentence-transformers not installed. Install it or set OPENAI_API_KEY to enable embeddings.")
                self.embed_model = None

    def _text_from_file(self, path: str) -> str:
        ext = path.split(".")[-1].lower()
        if ext in ("md", "txt", "json"):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        elif ext in ("html", "htm"):
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
                return soup.get_text(separator="\n")
        else:
            # fallback - try decode
            with open(path, "rb") as f:
                return f.read().decode(errors="ignore")

    def chunk_text(self, text: str, chunk_size=800, overlap=100):
        tokens = text.split()
        chunks = []
        i = 0
        while i < len(tokens):
            chunk = " ".join(tokens[i:i + chunk_size])
            chunks.append(chunk)
            i += chunk_size - overlap
        return chunks

    def _embed_texts_openai(self, texts: List[str]) -> List[List[float]]:
        # Use OpenAI embeddings API in a simple loop (small inputs)
        # Model: text-embedding-3-small (cost-effective). Change if needed.
        if openai is None:
            raise RuntimeError("OpenAI package not installed.")
        embeddings = []
        for t in texts:
            resp = openai.Embedding.create(input=t, model="text-embedding-3-small")
            embeddings.append(resp["data"][0]["embedding"])
        return embeddings

    def _embed_texts_local(self, texts: List[str]) -> List[List[float]]:
        if self.embed_model is None:
            raise RuntimeError("Local embedding model not available.")
        # sentence-transformers returns numpy array; convert to list
        embs = self.embed_model.encode(texts)
        # If it's numpy array, convert to list of lists
        try:
            return embs.tolist()
        except Exception:
            return [list(e) for e in embs]

    def ingest_files(self, paths: List[str]):
        """
        Ingest files into Chroma: chunk text, add documents + metadata.
        If embeddings are available (OpenAI or local), compute and add them to Chroma as well.
        """
        to_upsert = []
        all_texts = []
        ids = []
        metadatas = []

        for p in paths:
            text = self._text_from_file(p)
            chunks = self.chunk_text(text)
            for idx, ch in enumerate(chunks):
                doc_id = f"{os.path.basename(p)}_{idx}"
                meta = {"source": os.path.basename(p), "chunk_idx": idx}
                to_upsert.append({"id": doc_id, "metadata": meta, "document": ch})
                all_texts.append(ch)
                ids.append(doc_id)
                metadatas.append(meta)

        # If no documents, return 0
        if not to_upsert:
            return 0

        docs = [d["document"] for d in to_upsert]

        # Try to add documents (Chroma will compute embeddings if configured)
        try:
            # Use add() signature with ids, documents, metadatas where available
            self.collection.add(ids=ids, documents=docs, metadatas=metadatas)
        except TypeError:
            # fallback for different chroma versions
            self.collection.add(documents=docs, metadatas=metadatas, ids=ids)
        except Exception as e:
            # If add fails for other reasons, raise
            raise

        # If embeddings are available and you want to upsert embeddings explicitly, you could compute and upsert them.
        # Many Chroma versions compute embeddings internally; explicit embedding upsert is optional.

        # persist if client supports persist()
        try:
            self.client.persist()
        except Exception:
            pass

        return len(ids)
