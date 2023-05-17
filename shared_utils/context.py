from shared_utils.PineconeDatabase import PineconeDatabase
from shared_utils.configurations import configurations
from shared_utils.nlp import generate_embedding
from shared_utils.models import BacklogItem, ProductVision, ProjectStructure
from typing import List
import heapq
import json
import logging
from shared_utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


class Context:

    def __init__(self):
        self._vector_db = PineconeDatabase(configurations.get('pinecone', 'api_key'))

    def add_project_vision(self, vision: ProductVision):
        # Add the project vision to the vector database
        vector = generate_embedding(vision.title)
        self._vector_db.add_context('vision_context', vector, vision.__dict__)

    def get_project_vision(self):
        # Retrieve the project vision from the vector database
        vision = self._vector_db.fetch('vision_context', 'context')['vectors']['vision_context']['metadata']
        return vision

    def add_project_structure(self, project_structure: str):
        # Add the project structure to the vector database
        vector = generate_embedding(project_structure)
        self._vector_db.add_context('structure_context', vector, {'project_structure': project_structure})

    def get_project_structure(self):
        # Retrieve the project structure from the vector database
        project_structure = self._vector_db.fetch(
            'structure_context', 'context')['vectors']['structure_context']['metadata']['project_structure']
        return json.loads(project_structure)
