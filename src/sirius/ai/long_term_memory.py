import os
from enum import Enum
from typing import List, Dict, Any, Optional, cast, Tuple

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


class LongTermMemoryRecollection(DatabaseDocument):
    recollection: str
    l2_distance: float

    @staticmethod
    def get(search_result: Tuple) -> "LongTermMemoryRecollection":
        return LongTermMemoryRecollection(
            recollection=search_result[0].page_content,
            l2_distance=search_result[1]
        )


class LongTermMemory(DatabaseDocument):
    source: str
    document_type: LongTermMemoryDocumentType
    chunk_size: int
    chunk_overlap: int
    size: int
    file_name: str

    async def recollect(self, query: str, max_l2_distance: float = 0.25) -> List[LongTermMemoryRecollection]:
        recollection_list: List[LongTermMemoryRecollection] = []
        embedding: OpenAIEmbeddings = OpenAIEmbeddings(disallowed_special=(), openai_api_key=common.get_environmental_secret(EnvironmentSecret.OPEN_AI_API_KEY))  # type: ignore[call-arg]
        database_file: DatabaseFile = await DatabaseFile.get(self.file_name)
        faiss: FAISS = FAISS.deserialize_from_bytes(embeddings=embedding, serialized=database_file.data)
        search_vector = await embedding.aembed_query(query)

        for search_result in await faiss.asimilarity_search_with_score_by_vector(search_vector):
            long_term_memory_recollection: LongTermMemoryRecollection = LongTermMemoryRecollection.get(search_result)
            if long_term_memory_recollection.l2_distance < max_l2_distance:
                recollection_list.append(long_term_memory_recollection)

        return recollection_list

    @staticmethod
    async def remember_from_url(url: str, document_type: LongTermMemoryDocumentType) -> "LongTermMemory":
        temp_file_path: str = await common.download_file_from_url(url)
        return await LongTermMemory.remember(temp_file_path, document_type, source=url)

    @classmethod
    async def remember(cls, file_path: str, document_type: LongTermMemoryDocumentType, chunk_size: int = 2000, chunk_overlap: int = 200, is_delete_after: bool = True, source: str = "") -> "LongTermMemory":
        file_name: str = common.get_sha256_hash(file_path)
        long_term_memory: LongTermMemory | None = await LongTermMemory.find_by_file_name(file_name)

        if long_term_memory is None:
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
            long_term_memory = LongTermMemory(**metadata)
            database_file: DatabaseFile = DatabaseFile(file_name=common.get_sha256_hash(file_path), metadata=metadata, purpose=metadata["purpose"])
            database_file.load_data(vector_index)

            await database_file.save()
            await long_term_memory.save()

        if is_delete_after:
            common.run_in_separate_thread(os.remove, file_path)

        return long_term_memory

    @staticmethod
    async def find_by_file_name(file_name: str) -> Optional["LongTermMemory"]:
        long_term_memory_list: List[LongTermMemory] = cast(List[LongTermMemory], await LongTermMemory.find_by_query(LongTermMemory.model_construct(file_name=file_name)))

        if len(long_term_memory_list) == 0:
            return None
        elif len(long_term_memory_list) == 1:
            return long_term_memory_list[0]
        else:
            raise

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
