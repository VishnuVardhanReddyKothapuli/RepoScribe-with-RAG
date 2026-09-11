# RepoScribe-with-RAG

## This README is also created by using RepoScribe...
A toolset combining a Streamlit web application for automated README generation with a local Retrieval-Augmented Generation (RAG) pipeline for querying repository codebases.

## Overview

RepoScribe-with-RAG provides workspace tools for automating software documentation and performing vector search Q&A over codebases. The Streamlit web application extracts repository content using `GitLoader`, filters out binary and dependency files, builds a visual repository tree, and passes context to Google Gemini to generate structured README documentation. The local scripts enable cloning repository files into `output.md`, chunking document text, indexing embeddings in ChromaDB, and answering natural language queries using ChatGroq.

## Key Features

- **Auto-README Generator (`streamlit_app.py`)**: Uses `GitLoader` to retrieve repository files, filters unwanted directories and file types (`SKIP_DIRS`, `SKIP_EXTENSIONS`), builds a formatted file tree, and generates Markdown documentation via `ChatGoogleGenerativeAI`.
- **Repository Context Dumper (`loader.py`)**: Clones remote Git repositories using `GitLoader` and aggregates source code content along with source file metadata into a single `output.md` file.
- **Local RAG Pipeline (`main.py`)**: Processes `output.md` using `RecursiveCharacterTextSplitter` (chunk size 500, overlap 100), generates vector embeddings with `HuggingFaceEmbeddings`, indexes them into a `Chroma` vector store, and executes retrieval-backed prompts using `ChatGroq` (`llama-3.3-70b-versatile`).

## Tech Stack

- **Web Framework**: Streamlit
- **AI/LLM Framework**: LangChain (`langchain`, `langchain-community`, `langchain-core`, `langchain-google-genai`, `langchain-huggingface`, `langchain-chroma`, `langchain-text-splitters`, `langchainhub`)
- **LLM Providers**: Google Generative AI (`ChatGoogleGenerativeAI`), Groq (`ChatGroq`)
- **Embeddings & Vector Store**: HuggingFace Embeddings (`sentence-transformers`), ChromaDB (`chromadb`)
- **Repository Management**: GitPython (`GitLoader`)
- **Environment Management**: `python-dotenv`

## Project Structure

```text
.
├── .gitignore          # File specifying unversioned files to ignore
├── README.md           # Repository documentation
├── loader.py           # Script to clone a Git repo and write document content to output.md
├── main.py             # Script to build Chroma vectorstore and run RAG Q&A using ChatGroq
├── requirements.txt    # List of Python dependencies
└── streamlit_app.py    # Streamlit application for automated README generation
```

## Installation

Create and activate a virtual environment, then install the dependencies listed in `requirements.txt`:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Usage

### Run the Auto-README Generator App

Launch the Streamlit web application:

```bash
streamlit run streamlit_app.py
```

### Dump Repository Context to `output.md`

Run `loader.py` to clone a repository and save its content to `output.md`:

```bash
python loader.py
```

### Run Local RAG Q&A Script

Run `main.py` to index `output.md` into ChromaDB and query the codebase:

```bash
python main.py
```

## Configuration

The application uses `python-dotenv` to load environment variables from a `.env` file in the root directory:

```env
GOOGLE_API_KEY='your_google_gemini_key_here'
GROQ_API_KEY='your_groq_api_key_here'
```

- `GOOGLE_API_KEY`: Required for generating READMEs with `ChatGoogleGenerativeAI` in `streamlit_app.py`.
- `GROQ_API_KEY`: Required for executing LLM queries with `ChatGroq` in `main.py`.

## Contributing / License

Not specified