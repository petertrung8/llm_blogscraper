import json
from operator import index
import tqdm
import numpy as np

from minsearch import VectorSearch
from sentence_transformers import SentenceTransformer
from minsearch import Index


EMBEDDING_MODEL = "all-MiniLM-L6-v2"
INPUT_JSON = "tagged_posts_chunked.json"

def text_index(articles):
    index = Index(
    text_fields=["chunk", "title"],
    keyword_fields=[]
    )

    index.fit(articles)
    return index


def embedding_texts(texts, model):
    text_embeddings = []

    for d in tqdm.tqdm(texts):
        text = d['title'] + ' ' + d['chunk']
        v = model.encode(text)
        text_embeddings.append(v)

    text_embeddings = np.array(text_embeddings)
    return text_embeddings


def vector_index(articles, embedding_model):
    print("Generating embeddings...")
    embeddings = embedding_texts(articles, embedding_model)

    print("Building vector search index...")
    vindex = VectorSearch()
    vindex.fit(embeddings, articles)
    return vindex


def text_search(query, index):
    return index.search(query, num_results=5)


def vector_search(query, vindex, embedding_model):
    q = embedding_model.encode(query)
    return vindex.search(q, num_results=5)


def hybrid_search(query, text_index, vector_index, embedding_model):
    text_results = text_search(query, text_index)
    vector_results = vector_search(query, vector_index, embedding_model)
    
    # Combine and deduplicate results
    seen_ids = set()
    combined_results = []

    for result in text_results + vector_results:
        if result['id'] not in seen_ids:
            seen_ids.add(result['id'])
            combined_results.append(result)
    
    return combined_results


def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        articles = json.load(f)

    print(f"Loaded {len(articles)} articles/chunks.")

    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"Using embedding model: {EMBEDDING_MODEL}")

    index = text_index(articles)
    vindex = vector_index(articles, embedding_model)
    print("Indexes are ready.")

    query = "What is social magic"
    results = hybrid_search(query, index, vindex, embedding_model)

    for result in results:
        print(f"Title: {result['title']}")

if __name__ == "__main__":
    main()