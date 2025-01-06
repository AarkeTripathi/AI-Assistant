# from langchain.text_splitter import CharacterTextSplitter
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_community.vectorstores import FAISS
from langchain_unstructured import UnstructuredLoader
from unstructured.cleaners.core import clean_extra_whitespace, remove_punctuation

def load_document(document):
    text=""
    loader = UnstructuredLoader([document],
                                post_processors=[clean_extra_whitespace, remove_punctuation],
                                chunking_strategy="basic",
                                max_characters=1000000,
                                include_orig_elements=False,)
    # loader = UnstructuredLoader([document],  post_processors=[clean_extra_whitespace, remove_punctuation])
    docs = loader.load()
    for doc in docs:
        text=text+doc.page_content
    return text

# def get_text_chunks(text):
#     text_splitter = CharacterTextSplitter(
#         separator="\n",
#         chunk_size=1000,
#         chunk_overlap=200,
#         length_function=len
#     )
#     chunks = text_splitter.split_text(text)
#     return chunks


# def get_vectorstore(text_chunks):
#     embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
#     # embeddings = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
#     vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
#     return vectorstore