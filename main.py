
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import os
from dotenv import load_dotenv

load_dotenv()

groq_api_key = os.environ.get('GROQ_API_KEY')

with open("output.md", encoding="utf-8") as f:
    state = f.read()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 500, chunk_overlap = 100,
)

texts = text_splitter.split_documents([Document(page_content=state)])

vectorstore = Chroma(embedding_function=HuggingFaceEmbeddings())
vectorstore.add_documents(texts)   

retriever = vectorstore.as_retriever()

llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.3,
)

def format_docs(docs):
    return '\n'.join(doc.page_content for doc in docs)

prompt = ChatPromptTemplate.from_template(
    "Answer the question using the context below.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}\n\n"
    "Answer:"
)

rag_chain = (
    {'context': retriever | format_docs, 'question': RunnablePassthrough()}
    | prompt | llm | StrOutputParser()
)

print(rag_chain.invoke('What are the contents available?'))