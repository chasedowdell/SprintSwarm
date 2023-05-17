from shared_utils.PineconeDatabase import PineconeDatabase
from shared_utils.configurations import configurations
from shared_utils.models import BacklogItem
from typing import List
import heapq
import logging
from shared_utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


class BacklogWithEmbedding:

    def __init__(self):
        self._backlog = []
        self._vector_db = PineconeDatabase(configurations.get('pinecone', 'api_key'))

    def add_item(self, item: BacklogItem, embedding: list, namespace: str):
        logging.info('Adding backlog item')
        heapq.heappush(self._backlog, item)
        self._vector_db.add_backlog_item(item, embedding, namespace=namespace)

    def delete_item(self, item_id: List[str]):
        self._backlog = [item for item in self._backlog if item.item.id != item_id]
        heapq.heapify(self._backlog)
        self._vector_db.delete(item_id)

    def update_priority(self, item_id: int, new_priority: int):
        for item in self._backlog:
            if item.item.id == item_id:
                item.priority = new_priority
                heapq.heapify(self._backlog)
                break

    def search_items(self, query_embedding: list, num_results: int, namespace: str):
        item_ids = self._vector_db.search(query_embedding, num_results, namespace=namespace)
        return [item for item in self._backlog if item.item.id in item_ids]

    def get_backlog(self):
        return self._backlog
