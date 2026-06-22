import os
import tempfile
import streamlit as st

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

st.set_page_config(page_title="RAG PDF Chatbot")

st.title("📚 RAG PDF Chatbot")

@st.cache_resource
def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

embedding_model = get_embedding_model()

if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None

with st.sidebar:

    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"]
    )

    if st.button("Process Documents"):

        if uploaded_file is None:
            st.error("Please upload a PDF first")

        else:

            try:

                with st.spinner("Processing PDF..."):

                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=".pdf"
                    ) as tmp_file:

                        tmp_file.write(uploaded_file.getvalue())
                        pdf_path = tmp_file.name

                    loader = PyPDFLoader(pdf_path)
                    docs = loader.load()

                    splitter = RecursiveCharacterTextSplitter(
                        chunk_size=1000,
                        chunk_overlap=200
                    )

                    chunks = splitter.split_documents(docs)

                    vectorstore = FAISS.from_documents(
                        documents=chunks,
                        embedding=embedding_model
                    )

                    st.session_state.vectorstore = vectorstore

                    st.success("PDF Processed Successfully")

            except Exception as e:
                st.error(f"Error: {str(e)}")

if st.session_state.vectorstore is not None:

    retriever = st.session_state.vectorstore.as_retriever(
        search_kwargs={"k": 4}
    )

    llm = ChatMistralAI(
        model="mistral-small-latest",
        api_key=os.getenv("MISTRAL_API_KEY")
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a helpful AI assistant.
Use ONLY the provided context to answer the question.
If the answer is not present in the context,
say: I could not find the answer in the document.
"""
            ),
            (
                "human",
                """Context:
{context}
Question:
{question}
"""
            )
        ]
    )

    query = st.chat_input("Ask a question")

    if query:

        docs = retriever.invoke(query)

        context = "\n\n".join(
            [doc.page_content for doc in docs]
        )

        final_prompt = prompt.invoke(
            {
                "context": context,
                "question": query
            }
        )

        response = llm.invoke(final_prompt)

        st.write("### Answer")
        st.write(response.content)

else:
    st.info("Upload PDF and click Process Documents")
