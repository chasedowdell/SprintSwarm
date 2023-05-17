import pinecone
from typing import List, Any
from shared_utils.models import BacklogItem, CodeBaseFunction
from shared_utils.vector_database_base import VectorDatabaseBase
import logging
from shared_utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


class PineconeDatabase(VectorDatabaseBase):
    def __init__(self, api_key: str):
        pinecone.init(api_key=api_key, environment='asia-northeast1-gcp')
        active_indexes = pinecone.list_indexes()

        # TODO change to configurable index
        if 'sprintswarm' not in active_indexes:
            # TODO Remove hardcoded dimension
            self.index = pinecone.create_index('sprintswarm', dimension=1536)
        self.index = pinecone.Index('sprintswarm')
        logger.debug('Connected to sprintswarm index')

    def add_backlog_item(self, item: BacklogItem, vector: List[float], namespace: str) -> None:
        logging.debug(f'Adding {item.id} to backlog namespace')
        self.index.upsert(vectors=[{'id': item.id, 'values': vector, 'metadata':
                          {'priority': str(item.priority),
                           'assignee': str(item.assignee),
                           'status': str(item.status)}}], namespace=namespace)

    def add_code(self, code_base_func: CodeBaseFunction) -> None:
        logging.debug(f'Adding {code_base_func.id} to codebase namespace')
        metadata = {
            "id": code_base_func.id,
            "function_name": code_base_func.function_name,
            "file_path": code_base_func.file_path,
            "code": code_base_func.code,
            "description": code_base_func.description
        }
        self.index.upsert(vectors=[{'id': code_base_func.id, 'values': code_base_func.embedding,
                                    'metadata': metadata}], namespace='codebase')

    def add_context(self, context_id: str,  vector: List[float],  context: dict) -> None:
        logging.debug(f'Adding {context_id} to codebase namespace')
        self.index.upsert(vectors=[{'id': context_id, 'values': vector,
                                    'metadata': context}], namespace='context')

    def delete(self, vector_ids: List[str]):
        self.index.delete(vector_ids)

    def search(self, query_vector: List[float], num_relevant: int = 5, namespace: str = None):
        return self.index.query(
            query_vector, top_k=num_relevant, include_metadata=True, namespace=namespace
        )

    def fetch(self, element_id: Any, namespace: Any):
        return self.index.fetch(ids=[element_id], namespace=namespace)
