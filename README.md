# Teaching Assistant — RAG Powered Study Companion

A locally-running AI teaching assistant that lets you upload your study material (PDFs, notes) and interact with it through chat and an adaptive quiz system. Built entirely on open-source tools with no cloud APIs or costs.

## What It Does

- **Chat with your documents** — ask questions about your study material and get detailed, context-grounded answers
- **Auto quiz generation** — generates multiple choice questions directly from your uploaded content
- **Weak topic tracking** — tracks which questions you got wrong and flags those topics in the sidebar
- **Score summary** — shows your performance at the end of every quiz session
- **Fully local** — everything runs on your machine, no data leaves your system

## Architecture Overview

The project runs two separate pipelines depending on the task:

### Pipeline 1 — RAG (Chat)

```
User Question 
     │
Embed question using nomic-embed-text (via Ollama)
     │
ChromaDB similarity search → top 3 relevant chunks
     │
Inject chunks + question into prompt
     │
llama3.2:1b generates grounded answer (via Ollama)
     │
Response displayed in Streamlit chat UI
```

This is **Retrieval Augmented Generation**. Instead of relying on the model's training memory, the answer is grounded in your actual documents. The model only sees what's in your notes.

### Pipeline 2 — Direct LLM (Quiz)

```
Raw document text (saved at index time)
     │
Split into 500-word chunks, randomly sample 3
     │
Feed chunks directly into prompt
     │
llama3.2:1b generates MCQ questions
     │
Parser extracts Q, options, answer from response
     │
Quiz rendered in Streamlit UI
```

Quiz generation doesn't use RAG because it's a **creative task, not a retrieval task**. There's no query to match against; the model just needs raw content to generate questions from.

---

## Tech Stack

Streamlit - for chat interface, file upload, quiz rendering
LlamaIndex - for document loading, chunking, indexing, querying
ChromaDB - persistent local storage of embeddings
llama3.2:1b via Ollama - text generation, quiz generation,
nomic-embed-text via Ollama - converting text to semantic vectors

---

## How Embeddings Work

When you index a document, each chunk of text is passed through `nomic-embed-text` which converts it into a high-dimensional vector — a list of numbers that encodes the *meaning* of that text. Similar meaning = vectors that are close together in space.

When you ask a question, your question is also converted into a vector. ChromaDB finds the stored chunks whose vectors are closest to your question vector — this is **semantic search**. It works even when the exact words don't match, because the model understands meaning, not just keywords.

---

## Project Structure

```
teaching-assistant/
│
├── app.py              # Streamlit UI — chat tab, quiz tab, sidebar
├── rag_engine.py       # Core logic — indexing, querying, quiz generation, parsing
├── data/               # Drop your PDFs and text files here
├── storage/            # ChromaDB persists embeddings here (auto-generated)
└── README.md
```

---

## Key Functions

### `rag_engine.py`

**`load_and_index_documents()`**
Reads all files from the `data/` directory using `SimpleDirectoryReader`. Chunks the text, generates embeddings via `nomic-embed-text`, and stores them in ChromaDB at the `storage/` path. Returns both the LlamaIndex `index` object and `raw_texts` (plain text of all documents used for quiz generation).

**`get_query_engine(index)`**
Wraps the index in a query engine with `similarity_top_k=3` (retrieves top 3 relevant chunks per query) and injects a custom prompt template that instructs the model to answer like a teaching assistant — detailed, clear, educational.

**`generate_quiz(raw_texts, num_questions)`**
Splits raw document text into 500-word chunks and randomly samples 3 of them to ensure question variety across the document. Sends them directly to `llama3.2:1b` via `llm.complete()` with a structured prompt asking for MCQ output. Returns the raw string response.

**`parse_quiz(raw)`**
Parses the raw model output line by line, extracting questions (`Q:`), options (`A) B) C) D)`), answers (`Answer:`), and explanations. Handles inconsistent model formatting using regex. Defaults the answer to the first available option if the model omits the Answer line.

---

## Setup & Installation

### Prerequisites
- [Ollama](https://ollama.com) installed and running
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Python 3.11

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/teaching-assistant.git
cd teaching-assistant
```

### 2. Create environment and install dependencies
```bash
conda create -n teaching-assistant python=3.11
conda activate teaching-assistant
pip install llama-index llama-index-vector-stores-chroma llama-index-embeddings-ollama llama-index-llms-ollama chromadb streamlit
```

### 3. Pull required Ollama models
```bash
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

### 4. Run the app
```bash
streamlit run app.py
```

---

## Usage

1. Drop your PDF or `.txt` study files into the `data/` folder
2. Click **Index Documents** in the sidebar — this reads, chunks, and embeds your files
3. Use the **Chat** tab to ask questions about your material
4. Use the **Quiz** tab to generate and take a multiple choice quiz
5. Weak topics from incorrect answers are tracked in the sidebar

---

## Known Limitations

- **Scanned PDFs / handwritten notes** — `SimpleDirectoryReader` uses `pypdf` which extracts the text layer only. Scanned documents have no text layer so they return empty. Fix: add an OCR preprocessing step using `easyocr` or `pytesseract` before indexing.
- **Small model constraints** — `llama3.2:1b` is limited in reasoning ability. Quiz questions can sometimes be repetitive or have ambiguous options. Upgrading to `llama3.1:8b` or an API-based model like GPT-4o would significantly improve quality.
- **No memory between sessions** — chat history is stored in Streamlit session state and resets on page refresh. A persistent conversation store (e.g. SQLite) would be needed for long-term memory.
- **Re-indexing on every upload** — currently re-embeds all documents on every index click. A smarter system would detect new files and only embed the delta.

---

## Possible Extensions

- **Socratic mode** — instead of answering directly, the assistant asks a leading question to guide the student to the answer themselves
- **OCR support** — preprocess scanned PDFs with `easyocr` before indexing
- **RAG evaluation** — use [RAGAS](https://github.com/explodinggradients/ragas) to score retrieval quality on faithfulness, answer relevance, and context recall
- **Hybrid search** — combine vector similarity search with BM25 keyword search for better retrieval on technical terms
- **Reranking** — pass retrieved chunks through a cross-encoder reranker (Cohere API) before sending to the LLM

---

## Why This Project

Built as a practical introduction to RAG systems and GenAI application development. The goal was to understand the full pipeline — from raw documents to embedded vectors to grounded LLM responses — by building something actually useful.
