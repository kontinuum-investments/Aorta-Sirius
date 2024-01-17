import os
from enum import Enum
from typing import List, Dict, Any

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, UnstructuredMarkdownLoader, TextLoader
from langchain_community.document_loaders.base import BaseLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from sirius import common
from sirius.constants import EnvironmentSecret
from sirius.database import DatabaseDocument, DatabaseFile


class LongTermMemoryDocumentType(Enum):
    TEXT: str = "TEXT"
    MARKDOWN: str = "MARKDOWN"
    PDF: str = "PDF"
    CSV: str = "CSV"


class LongTermMemory(DatabaseDocument):
    source: str
    document_type: LongTermMemoryDocumentType
    chunk_size: int
    chunk_overlap: int
    size: int
    file_name: str

    @staticmethod
    async def remember_from_url(url: str, document_type: LongTermMemoryDocumentType) -> "LongTermMemory":
        temp_file_path: str = await common.download_file_from_url(url)
        return await LongTermMemory.remember(temp_file_path, document_type, source=url)

    @classmethod
    async def recollect(cls, query: str, long_term_memory: "LongTermMemory", max_l2_distance: float = 0.25) -> List[str]:
        recollection_list: List[str] = []
        embedding: OpenAIEmbeddings = OpenAIEmbeddings(disallowed_special=(), openai_api_key=common.get_environmental_secret(EnvironmentSecret.OPEN_AI_API_KEY))  # type: ignore[call-arg]
        database_file: DatabaseFile = await DatabaseFile.get(long_term_memory.file_name)
        faiss: FAISS = FAISS.deserialize_from_bytes(embeddings=embedding, serialized=database_file.data)
        search_vector = await embedding.aembed_query(query)

        for recollection in await faiss.asimilarity_search_with_score_by_vector(search_vector):
            if recollection[1] < max_l2_distance:
                recollection_list.append(recollection[0].page_content)

        return recollection_list

    @classmethod
    async def remember(cls, file_path: str, document_type: LongTermMemoryDocumentType, chunk_size: int = 2000, chunk_overlap: int = 200, is_delete_after: bool = True, source: str = "") -> "LongTermMemory":
        source = file_path if source is None else source
        file_name: str = source if source != "" else common.get_unique_id()
        vector_index: bytes = LongTermMemory._get_faiss(file_path, document_type, chunk_size, chunk_overlap).serialize_to_bytes()
        metadata: Dict[str, Any] = {
            "purpose": cls.__name__,
            "source": source,
            "document_type": document_type.value,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "size": len(vector_index),
            "file_name": file_name
        }
        database_file: DatabaseFile = DatabaseFile(file_name=file_name, metadata=metadata, purpose=metadata["purpose"])
        database_file.load_data(vector_index)

        await database_file.save()
        long_term_memory: LongTermMemory = LongTermMemory(**metadata)
        await long_term_memory.save()

        if is_delete_after:
            common.run_in_separate_thread(os.remove, file_path)

        return long_term_memory

    @staticmethod
    def _get_faiss(file_path: str, document_type: LongTermMemoryDocumentType, chunk_size: int = 500, chunk_overlap: int = 50) -> FAISS:
        text_splitter: RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        embedding: OpenAIEmbeddings = OpenAIEmbeddings(disallowed_special=(), openai_api_key=common.get_environmental_secret(EnvironmentSecret.OPEN_AI_API_KEY))  # type: ignore[call-arg]

        if document_type == LongTermMemoryDocumentType.MARKDOWN:
            loader: BaseLoader = UnstructuredMarkdownLoader(file_path)
        elif document_type == LongTermMemoryDocumentType.PDF:
            loader = PyPDFLoader(file_path, extract_images=True)
        elif document_type == LongTermMemoryDocumentType.CSV:
            loader = CSVLoader(file_path)
        else:
            loader = TextLoader(file_path)

        return FAISS.from_documents(text_splitter.split_documents(loader.load()), embedding)
