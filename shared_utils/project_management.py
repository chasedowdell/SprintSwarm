from enum import Enum


class Status(Enum):
    TODO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class BacklogItem:
    def __init__(self, title, description, priority, status=Status.TODO, assignee=None):
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status
        self.assignee = assignee

    def update(self, title=None, description=None, priority=None, status=None, assignee=None):
        if title is not None:
            self.title = title
        if description is not None:
            self.description = description
        if priority is not None:
            self.priority = priority
        if status is not None:
            self.status = status
        if assignee is not None:
            self.assignee = assignee


class Backlog:
    def __init__(self):
        self.items = []

    def create_item(self, title, description, priority, status=Status.TODO, assignee=None):
        item = BacklogItem(title, description, priority, status, assignee)
        self.items.append(item)
        return item

    def delete_item(self, item):
        self.items.remove(item)

    def filter_by_status(self, status):
        return [item for item in self.items if item.status == status]

    def filter_by_assignee(self, assignee):
        return [item for item in self.items if item.assignee == assignee]

    def sort_by_priority(self):
        self.items.sort(key=lambda item: item.priority)
