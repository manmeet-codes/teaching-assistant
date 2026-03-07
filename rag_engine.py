from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
from llama_index.core import PromptTemplate
import chromadb
import re
import random

# ---- Configuration ----
DATA_DIR = "data"
STORAGE_DIR = "storage"
MODEL_NAME = "llama3.2:1b"
EMBED_MODEL_NAME = "nomic-embed-text"

# ---- Global Settings ----
Settings.llm = Ollama(model=MODEL_NAME, request_timeout=120.0)
Settings.embed_model = OllamaEmbedding(model_name=EMBED_MODEL_NAME)


def load_and_index_documents():
    documents = SimpleDirectoryReader(DATA_DIR).load_data()
    chroma_client = chromadb.PersistentClient(path=STORAGE_DIR)
    chroma_collection = chroma_client.get_or_create_collection("teaching_assistant")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
    raw_texts = [doc.text for doc in documents]
    return index, raw_texts


def get_query_engine(index):
    qa_prompt = PromptTemplate(
        "You are a helpful teaching assistant. "
        "Using the context below, answer the question in detail. "
        "Explain clearly as if teaching a student. Be thorough.\n\n"
        "Context:\n{context_str}\n\n"
        "Question: {query_str}\n\n"
        "Detailed Answer:"
    )
    query_engine = index.as_query_engine(similarity_top_k=3)
    query_engine.update_prompts({"response_synthesizer:text_qa_template": qa_prompt})
    return query_engine


def generate_quiz(raw_texts, num_questions=3):
    llm = Ollama(model=MODEL_NAME, request_timeout=180.0)

    # split into chunks and pick random ones for variety
    words = " ".join(raw_texts).split()
    chunks = [" ".join(words[i:i+500]) for i in range(0, len(words), 500)]
    selected = random.sample(chunks, min(3, len(chunks)))
    context = " ".join(selected)

    prompt = f"""Read the material below and generate {num_questions} multiple choice questions.

Material:
{context}

Rules:
- Each question must have 4 options: A) B) C) D)
- Each question must have one correct Answer
- Use exactly this format for every question:

Q: your question here
A) option one
B) option two
C) option three
D) option four
Answer: B

Q: next question here
A) option one
B) option two
C) option three
D) option four
Answer: D

Generate {num_questions} questions now:"""

    response = llm.complete(prompt)
    return str(response).strip()


def parse_quiz(raw):
    questions = []
    current = None

    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith("Q:"):
            # save previous question if valid
            if current and current["question"] and len(current["options"]) >= 2:
                if not current["answer"]:
                    current["answer"] = list(current["options"].keys())[0]
                questions.append(current)
            current = {"question": "", "options": {}, "answer": "", "explanation": ""}
            current["question"] = line[2:].strip()

        elif current is None:
            continue

        elif re.match(r'^A[\):\s]', line, re.IGNORECASE):
            current["options"]["A"] = re.sub(r'^A[\):\s]+', '', line, flags=re.IGNORECASE).strip()
        elif re.match(r'^B[\):\s]', line, re.IGNORECASE):
            current["options"]["B"] = re.sub(r'^B[\):\s]+', '', line, flags=re.IGNORECASE).strip()
        elif re.match(r'^C[\):\s]', line, re.IGNORECASE):
            current["options"]["C"] = re.sub(r'^C[\):\s]+', '', line, flags=re.IGNORECASE).strip()
        elif re.match(r'^D[\):\s]', line, re.IGNORECASE):
            current["options"]["D"] = re.sub(r'^D[\):\s]+', '', line, flags=re.IGNORECASE).strip()

        elif re.match(r'^Answer', line, re.IGNORECASE):
            match = re.search(r'[ABCD]', line.upper())
            if match:
                current["answer"] = match.group()

        elif re.match(r'^Explanation', line, re.IGNORECASE):
            current["explanation"] = line.split(":", 1)[-1].strip()

    # save last question
    if current and current["question"] and len(current["options"]) >= 2:
        if not current["answer"]:
            current["answer"] = list(current["options"].keys())[0]
        questions.append(current)

    return questions