import streamlit as st
import tempfile
import os
import re
from langchain_community.document_loaders import GitLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

MAX_CODE_CHARS = 60_000
MAX_FILE_CHARS = 5_000

KEY_FILENAMES = {
    "main.py", "app.py", "index.py", "server.py", "manage.py",
    "requirements.txt", "setup.py", "pyproject.toml",
    "package.json", "tsconfig.json",
    "Cargo.toml", "go.mod", "Gemfile",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "Makefile",
    "README.md", "CONTRIBUTING.md", "LICENSE",
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
    ".java", ".rb", ".c", ".cpp", ".h", ".cs", ".swift",
    ".kt", ".scala", ".php", ".vue", ".svelte",
    ".yaml", ".yml", ".toml", ".cfg", ".ini", ".json",
}

SKIP_DIRS = {
    "node_modules", ".venv", "__pycache__", ".next",
    "dist", "build", ".idea", ".vscode", ".git",
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pyc", ".pyo", ".so", ".dll", ".exe",
    ".bin", ".dat", ".db", ".sqlite",
    ".zip", ".tar", ".gz", ".pdf", ".lock",
}

SYSTEM_PROMPT = """You are a senior software documentation engineer. Generate a complete, 
accurate README.md using ONLY the code and documentation provided below. 
Never invent features, dependencies, commands, or setup steps that aren't 
evidenced in the given content. If something is missing (license, env vars, 
tests), omit that section or write "Not specified" — do not guess.

Output pure Markdown only. No preamble, no explanation, no code fences 
wrapping the whole thing — just the README content itself.

Structure, in this order (skip a section only if there's truly nothing 
to base it on):
1. Project title + one-line description
2. Overview — 2-4 sentences on what it does and why, grounded in the code
3. Key Features — bullets, each traceable to actual code/functions you saw
4. Tech Stack — only libraries/frameworks you can confirm from imports, 
   requirements.txt, package.json, Dockerfile, etc.
5. Project Structure — a short tree with one-line purpose per top-level 
   folder/file, based on the file tree given
6. Installation — exact commands, derived from actual dependency/setup files
7. Usage — real example commands or code snippets found in the repo 
   (entry points, main.py, CLI args, etc.)
8. API Reference — only if you found route/endpoint definitions (FastAPI, 
   Flask, Express, etc.); list method + path + one-line purpose
9. Configuration — env vars only if a .env.example or config file was provided
10. Contributing / License — only if a CONTRIBUTING.md or LICENSE file 
    was included in the docs"""

USER_TEMPLATE = """Repository: {repo_name}

File Tree:
{file_tree}

Code Context (key files, truncated as needed):
{code_context}

Internal Documentation (README fragments, docstrings, wikis, etc.):
{docs_context}

Generate the README.md following the system prompt's structure and 
grounding rules. Every claim must trace back to the content above."""


def file_filter(path: str) -> bool:
    """Skip binary / generated / dependency directories."""
    parts = path.replace("\\", "/").split("/")
    if any(p in SKIP_DIRS for p in parts):
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in SKIP_EXTENSIONS:
        return False
    return True


def extract_repo_name(url: str) -> str:
    match = re.search(r"github\.com/([^/]+/[^/]+)", url.rstrip("/").removesuffix(".git"))
    return match.group(1) if match else url


def build_file_tree(docs) -> str:
    """Render a visual tree from loaded document sources."""
    sources = sorted({doc.metadata.get("source", "") for doc in docs})
    tree: dict = {}
    for src in sources:
        parts = src.replace("\\", "/").strip("/").split("/")
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    def render(node, prefix=""):
        lines = []
        items = sorted(node.keys())
        for i, name in enumerate(items):
            last = i == len(items) - 1
            connector = "└── " if last else "├── "
            lines.append(f"{prefix}{connector}{name}")
            if node[name]:
                extension = "    " if last else "│   "
                lines.extend(render(node[name], prefix + extension))
        return lines

    return "\n".join(render(tree))


def extract_code_context(docs) -> str:
    """Select key code files, truncate, and concatenate."""
    selected, budget = [], MAX_CODE_CHARS

    priority = [d for d in docs if os.path.basename(d.metadata.get("source", "")) in KEY_FILENAMES]
    others = [
        d for d in docs
        if os.path.basename(d.metadata.get("source", "")) not in KEY_FILENAMES
        and os.path.splitext(d.metadata.get("source", ""))[1] in CODE_EXTENSIONS
    ]

    for doc in priority + others:
        if budget <= 0:
            break
        source = doc.metadata.get("source", "")
        content = doc.page_content[:MAX_FILE_CHARS]
        selected.append(f"## {source}\n\n{content}")
        budget -= len(content)

    return "\n\n---\n\n".join(selected) if selected else "No code files found."


def extract_docs_context(docs) -> str:
    """Pull out markdown / text documentation files."""
    entries = []
    for doc in docs:
        source = doc.metadata.get("source", "")
        ext = os.path.splitext(source)[1].lower()
        if ext in {".md", ".rst", ".txt"}:
            entries.append(f"## {source}\n\n{doc.page_content[:MAX_FILE_CHARS]}")
    return "\n\n---\n\n".join(entries) if entries else "No internal documentation found."


st.set_page_config(page_title="README Generator", page_icon="📄", layout="centered")

st.title("📄 README.md Generator")
st.caption("Paste a public GitHub repository URL to auto-generate a professional README")

api_key = os.environ.get("GOOGLE_API_KEY", "")


repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/user/repo",
)

if st.button("🚀 Generate README", type="primary", disabled=not repo_url, use_container_width=True):
    if not api_key:
        st.error("GOOGLE_API_KEY not found in .env file.")
        st.stop()

    repo_name = extract_repo_name(repo_url)

    with st.status("Generating README…", expanded=True) as status:
        st.write("🔄 Cloning repository…")
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                loader = GitLoader(
                    repo_path=tmpdir,
                    clone_url=repo_url,
                    file_filter=file_filter,
                )
                docs = loader.load()

                if not docs:
                    st.error("No files found in the repository. Is the URL correct and the repo public?")
                    st.stop()

                st.write(f"✅ Loaded **{len(docs)}** files")

                st.write("🌳 Building file tree & extracting context…")
                file_tree = build_file_tree(docs)
                code_context = extract_code_context(docs)
                docs_context = extract_docs_context(docs)

                st.write("🤖 Generating README with LLM…")
                llm = ChatGoogleGenerativeAI(
                    model="gemini-3.6-flash",
                    temperature=0.3,
                    google_api_key=api_key,
                )
                prompt = ChatPromptTemplate.from_messages([
                    ("system", SYSTEM_PROMPT),
                    ("human", USER_TEMPLATE),
                ])
                chain = prompt | llm | StrOutputParser()

                readme_content = chain.invoke({
                    "repo_name": repo_name,
                    "file_tree": file_tree,
                    "code_context": code_context,
                    "docs_context": docs_context,
                })

                status.update(label="✅ README generated!", state="complete")

        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.stop()

    st.divider()
    st.subheader("Generated README.md")

    tab_preview, tab_raw = st.tabs(["📖 Preview", "📝 Raw Markdown"])
    with tab_preview:
        st.markdown(readme_content)
    with tab_raw:
        st.code(readme_content, language="markdown")

    st.download_button(
        "⬇️ Download README.md",
        readme_content,
        file_name="README.md",
        mime="text/markdown",
        use_container_width=True,
    )
