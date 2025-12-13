from sentence_transformers import SentenceTransformer, util
import os
os.environ["HF_HUB_DISABLE_AUTO_CONVERSION"] = "1"
model = SentenceTransformer("BAAI/bge-m3")

emb1 = model.encode("This is a test sentence.", normalize_embeddings=True)
emb2 = model.encode("This is Nepal .", normalize_embeddings=True)

similarity = util.cos_sim(emb1, emb2)
print("Cosine similarity:", similarity.item())