from langchain_community.document_loaders import GitLoader


loader = GitLoader('/loader.py','https://github.com/Repo')

docs = loader.load()



with open("output.md", "w", encoding="utf-8") as f:
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        f.write(f"## {source}\n\n")
        f.write(doc.page_content)
        f.write("\n\n---\n\n")

print("Done! Check output.md")