# 📄 LangChain Multi-Tool Project

A powerful workspace combining multiple AI-driven functionalities into a single repository. This project features a fully functional **Streamlit-based Auto-README Generator** powered by Google Gemini, alongside local scripts for building **Retrieval-Augmented Generation (RAG)** pipelines over GitHub repositories and local documents.

---

## ✨ Features

- **Auto-README Generator (Streamlit App)**
  - Enter any public GitHub repository URL to auto-generate a professional `README.md`.
  - Intelligently filters out binary files and dependency folders to fit code into context windows.
  - Generates READMEs completely locally in your browser using **Google Gemini** models.
  - Provides instant previews and 1-click Markdown downloads.

- **Local RAG Pipeline (Core Scripts)**
  - Clones and processes GitHub repositories directly using LangChain's `GitLoader`.
  - Chunks, embeds, and indexes document context using `sentence-transformers` and **ChromaDB**.
  - Queries local repositories via LangChain with an LLM of your choice.

---

## 🧩 Tech Stack

- **Frameworks:** [Streamlit](https://streamlit.io/), [LangChain](https://python.langchain.com/)
- **LLM Providers:** [Google GenAI (Gemini)](https://ai.google.dev/)
- **Vector Store:** ChromaDB
- **Embeddings:** HuggingFace (`sentence-transformers`)

---

## 📁 Project Structure

```text
langchain-project/
├── streamlit_app.py     # Main Streamlit web app for auto-generating READMEs
├── main.py              # Local RAG Q&A script using ChromaDB + LangChain
├── loader.py            # Utility script for cloning and dumping GitHub repos to output.md
├── requirements.txt     # Project Python dependencies
└── .env                 # Environment variables (GOOGLE_API_KEY, GROQ_API_KEY)
```

---

## 📋 Prerequisites

Ensure you have Python installed, and create a virtual environment:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

> **Note on Python 3.14+:** Some ML libraries (like `sentence-transformers`) may require `torchvision` or face thread shutdown bugs. If you encounter a `ModuleNotFoundError` during Streamlit runs, run `pip install torchvision`.

---

## ⚙️ Configuration

Create a `.env` file in the root directory and add your API keys:

```env
GOOGLE_API_KEY='your_google_gemini_key_here'
GROQ_API_KEY='your_groq_api_key_here' # Optional, if you want to run the older main.py script
```

---

## 🚀 Usage

### 1. Auto-README Generator (Web App)

Run the Streamlit application to launch the web interface:

```bash
streamlit run streamlit_app.py
```

- Open `http://localhost:8501` in your browser.
- Paste a GitHub URL, and let Gemini generate your documentation!

### 2. Local Repo Loader & RAG Scripts

To clone a repo and dump all context into a single Markdown file (`output.md`):

```bash
python loader.py
```

To run the local Retrieval-Augmented Generation question-answering script on `output.md`:

```bash
python main.py
```
# RepoScribe-with-RAG
