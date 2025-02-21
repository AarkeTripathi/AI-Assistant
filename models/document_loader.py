'''Extraction through API (Online)'''

import os
from dotenv import load_dotenv
import time
from unstract.llmwhisperer import LLMWhispererClientV2

class DocumentLoader:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv('LLMWHISPERER_API_KEY')
        self.client = LLMWhispererClientV2(api_key=api_key)

    def load_document(self, document):
        result = self.client.whisper(file_path=document)
        if result["status_code"] == 202:
            while True:
                status = self.client.whisper_status(whisper_hash=result["whisper_hash"])
                if status["status"] == "processed":
                    resultx = self.client.whisper_retrieve(whisper_hash=result["whisper_hash"])
                    return resultx['extraction']['result_text']
                time.sleep(5)



'''Extraction through Computation'''

# from langchain_unstructured import UnstructuredLoader
# from unstructured.cleaners.core import clean_extra_whitespace, remove_punctuation

# def load_document(document):
#     text=""
#     loader = UnstructuredLoader([document],
#                                 post_processors=[clean_extra_whitespace, remove_punctuation],
#                                 chunking_strategy="basic",
#                                 max_characters=1000000,
#                                 include_orig_elements=False,)
#     docs = loader.load()
#     for doc in docs:
#         text=text+doc.page_content
#     return text