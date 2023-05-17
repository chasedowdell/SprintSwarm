from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Dict, Optional
from pydantic import BaseModel

BACKLOG_STATUS = {0: 'TODO', 1: 'IN_PROGRESS', 2: 'DONE'}

@dataclass(order=True)
class BacklogItem:
    priority: int
    item: Any = field(compare=False)

    def __post_init__(self):
        self.id = str(hash(self.item['description']))
        self.status = 0
        self.assignee = None


class ProductVision(BaseModel):
    title: str
    description: str
    goals: List[str]
    key_features: List[str]
    constraints: List[str]


class ProjectStructure(BaseModel):
    project_philosophy: str
    files: List[Dict[str, str]]


class CodeBaseFunction(BaseModel):
    id: str
    file_path: str
    function_name: str
    code: str
    embedding: List[float]
    description: str


class WorkItemUpdate(BaseModel):
    id: str
    is_updated: bool
    work_item: Dict[str, Any]  # The work item data (e.g., code changes)
    additional_info: Optional[Dict[str, Any]]  # Any additional information related to the work item update

class ProjectFile(BaseModel):
    file_path: str
    content: str
