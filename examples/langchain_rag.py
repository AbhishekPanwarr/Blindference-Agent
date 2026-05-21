"""RAG (Retrieval-Augmented Generation) with Blindference + LangChain.

This example shows how to use BlindferenceLLM as the generation backend
for a LangChain RAG pipeline. All LLM calls are encrypted end-to-end."""

import os

from langchain import OpenAIEmbeddings  # or any embedding model
from langchain.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA

# Import the Blindference LangChain integration
from blindference_agent.integrations.langchain import BlindferenceLLM


def main():
    # 1 — Create a local vector store (documents about confidential computing)
    documents = [
        "Confidential computing uses hardware-based Trusted Execution Environments (TEEs) to protect data in use.",
        "Fully Homomorphic Encryption (FHE) allows computation on encrypted data without decryption.",
        "Blindference combines FHE with quorum-based inference to ensure AI results are trustworthy.",
        "A quorum of nodes (1 leader + 2 verifiers) runs the same model and reaches consensus via hash matching.",
    ]

    text_splitter = CharacterTextSplitter(chunk_size=200, chunk_overlap=20)
    docs = text_splitter.create_documents(documents)

    embeddings = OpenAIEmbeddings()  # Replace with local embeddings if preferred
    vectorstore = Chroma.from_documents(docs, embeddings)

    # 2 — Initialize Blindference LLM
    llm = BlindferenceLLM(
        icl_url=os.environ.get("BLF_ICL_URL", "https://icl.blindference.xyz"),
        cofhe_rpc=os.environ.get("BLF_COFHE_RPC", ""),
        private_key=os.environ.get("BLF_PRIVATE_KEY", ""),
        model="groq:llama-3.3-70b-versatile",
        verifier_count=2,
    )

    # 3 — Build RAG chain
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(),
    )

    # 4 — Ask a question (encrypted end-to-end)
    query = "How does Blindference ensure AI results are trustworthy?"
    print(f"Query: {query}\n")
    result = qa.invoke(query)
    print(f"Answer: {result['result']}")


if __name__ == "__main__":
    main()
