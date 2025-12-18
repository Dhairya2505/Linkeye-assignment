from fastapi import FastAPI
from playwright.sync_api import sync_playwright
import time
import hashlib
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
from pydantic import BaseModel
from collections import defaultdict
from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found in .env")

model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2,
    max_tokens=2500,
    timeout=None,
    max_retries=2
)

URL = "https://api.freshservice.com/"
CONTENT_SELECTOR = ".api-content-main"

class Item(BaseModel):
    query: str

def split_documents(documents, chunk_size=500, chunk_overlap=120):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=[
            "\n\n## ",
            "\n\n### ",
            "\n\n",
            "\n- ",
            "\n* ",
            "\n",
            " "
        ]
    )

    chunks = splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks")
    return chunks

def build_embedding_text(doc):
    parts = []

    if "parent_id" in doc.metadata:
        parts.append(f"Document section: {doc.metadata['parent_id']}")

    if "anchor_id" in doc.metadata:
        parts.append(f"Subsection: {doc.metadata['anchor_id']}")

    parts.append(doc.page_content)

    return "\n".join(parts)

def embed_documents(chunks, model_name="multi-qa-MiniLM-L6-cos-v1"):
    model = SentenceTransformer(model_name)

    texts = [build_embedding_text(doc) for doc in chunks]

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    return embeddings

def retrieve_chunks(query, index, id_to_doc, k=20):
    model = SentenceTransformer("multi-qa-MiniLM-L6-cos-v1")
    query_emb = model.encode(
        query,
        normalize_embeddings=True
    ).reshape(1, -1)

    D, I = index.search(query_emb, k)

    results = []
    for score, idx in zip(D[0], I[0]):
        if idx == -1:
            continue

        doc = id_to_doc[idx]
        results.append({
            "doc": doc,
            "score": float(score)
        })

    return results


@app.get("/ingest-data", status_code=200)
def data_ingestion():
    data = []
    seen_hashes = set()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, timeout=60000)
        page.wait_for_load_state("networkidle")

        sections = page.evaluate("""
        () => Array.from(document.querySelectorAll('div.scroll-spy'))
        .map(el => ({
            id: el.id,
            parent_id: el.parentElement ? el.parentElement.id : null
        }))
        .filter(obj => obj.id)
        """)

        for sec in sections:
            sid = sec["id"]
            parent_id = sec["parent_id"]

            page.evaluate(
                "id => document.getElementById(id).scrollIntoView({block:'start'})",
                sid
            )

            time.sleep(0.5)

            content = page.evaluate("""
            (id) => {
                const section = document.getElementById(id);
                if (!section) return '';

                const contentDiv = section.querySelector('.api-content-main');
                if (!contentDiv) return '';

                return contentDiv.innerText.trim();
            }
            """, sid)
            
            if not content:
                continue
            
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if content_hash in seen_hashes:
                continue

            seen_hashes.add(content_hash)
            data.append({
                "page_content":content,
                "source": URL,
                "anchor_id": sid,
                "parent_id": parent_id
            })

        browser.close()


    documents = []
    for d in data:
        documents.append(Document(
            page_content=d["page_content"],
            metadata={
                "anchor_id": d["anchor_id"],
                "parent_id": d["parent_id"],
                "source": d["source"],
                "content_length": len(d["page_content"]),
                "has_code": "```" in d["page_content"],
            }
        ))

    chunks = split_documents(documents)
    for c in chunks:
        header = c.metadata.get("anchor_id", "")
        if header:
            c.page_content = f"[Section: {header}]\n{c.page_content}"
    
    for i, c in enumerate(chunks):
        c.metadata["chunk_index"] = i

    embeddings = embed_documents(chunks)

    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)
    index = faiss.IndexIDMap(index)

    ids = np.arange(len(embeddings))
    index.add_with_ids(embeddings, ids)

    id_to_doc = {i: chunks[i] for i in range(len(chunks))}

    faiss.write_index(index, "docs.index")
    np.save("embeddings.npy", embeddings)

    with open("docstore.pkl", "wb") as f:
        pickle.dump(id_to_doc, f)
    return {
        "message": "Data ingested successfully"
    }

@app.post("/get-answer", status_code=201)
def get_answer(query: Item):
    
    index = faiss.read_index("docs.index")

    with open("docstore.pkl", "rb") as f:
        id_to_doc = pickle.load(f)

    chunks = retrieve_chunks(query.query, index, id_to_doc)

    print("Total retrieved chunks:", len(chunks))
    print("Sample scores:", [r["score"] for r in chunks[:5]])
    print("Parents:", {r["doc"].metadata.get("parent_id") for r in chunks})

    if not chunks:
        return {
            "answer": "I don't have enough information in the provided documents.",
            "top_anchor_id": None,
            "score": None
        }

    grouped = defaultdict(list)
    for doc in chunks:
        chunk = doc["doc"]
        grouped[chunk.metadata["parent_id"]].append(chunk)

    section_scores = defaultdict(float)
    section_docs = defaultdict(list)

    for item in chunks:
        doc = item["doc"]
        score = item["score"]

        parent = doc.metadata.get("parent_id")
        if not parent:
            continue

        section_docs[parent].append(item)
        section_scores[parent] = max(section_scores[parent], score)
    

    if not section_scores:
        return {
            "answer": "I don't have enough information in the provided documents.",
            "top_anchor_id": None,
            "score": None
        }

    best_section = max(section_scores.items(), key=lambda x: x[1])
    best_parent_id, best_score = best_section

    best_chunk = max(
        section_docs[best_parent_id],
        key=lambda x: x["score"]
    )

    best_anchor_id = best_chunk["doc"].metadata.get("anchor_id")

    context_parts = []

    for parent, docs in grouped.items():
        section_text = "\n".join(d.page_content for d in docs)
        block = f"### Section: {parent}\n{section_text}"
        context_parts.append(block)

    context = "\n\n".join(context_parts)[:5000]

    prompt = f"""
    You are a technical assistant.
    Answer ONLY using the provided context. Explain the answer in detail unsing the context.
    Generate a readable answer with proper spacing.
    If the answer is not present in the context, say:
    "I don't have enough information in the provided documents."
    Do not use prior knowledge.

    Context:
    {context}

    Answer:
    
    """

    messages = [
        (
            "system",
            prompt
        ),
        ("human", query.query),
    ]
    ai_msg = model.invoke(messages)
    return {
        "answer" : ai_msg.content,
        "top_anchor_id": best_anchor_id,
        "score": round(best_score, 4)
    }