import os
import shutil

from llama_index.core import Settings, VectorStoreIndex, StorageContext, Document
from llama_index.vector_stores.deeplake import DeepLakeVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter


class VectorDB:
    def __init__(self, dataset_path=None, chunk_size=512, overlap=50):
        self.dataset_path = dataset_path
        self.chunk_size = chunk_size
        self.overlap = overlap

        Settings.embed_model = OpenAIEmbedding(
            model="text-embedding-3-small"
        )

        self.parser = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap
        )

        self.index = None

        if self.dataset_path:
            self._build_persistent_index()

    def _build_persistent_index(self):
        self.vector_store = DeepLakeVectorStore(
            dataset_path=self.dataset_path
        )

        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            storage_context=self.storage_context
        )



    def build_ephemeral_complaint_index(self, complaint_documents: list[Document]):
        

        if not complaint_documents:
            return None

        nodes = self.parser.get_nodes_from_documents(complaint_documents)

        return VectorStoreIndex(nodes)

    def get_filter_index(self):
        """
        Returns the persistent filter-resolution index.
        """

        if self.index is None:
            raise ValueError("Persistent filter index has not been initialized")

        return self.index

    def get_parser(self):
        return self.parser