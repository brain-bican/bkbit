from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain.document_loaders import PyPDFLoader



def load_pdf(path: str):
    """
    Loads a PDF and returns a list of Document objects.
    """
    loader = PyPDFLoader(path)
    # This returns a list of Documents, one per page
    documents = loader.load()
    return documents


def split_documents(documents, chunk_size=1000, chunk_overlap=200):
    """
    Splits each Document into smaller chunks of text.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    split_docs = []
    for doc in documents:
        for chunk in text_splitter.split_text(doc.page_content):
            split_docs.append(Document(page_content=chunk, metadata=doc.metadata))
    return split_docs

