"""Task management operations mixin."""

from typing import Any, Dict, List, Optional

from ..exceptions import NotFoundError
from ..models import Task, TaskStatus, TaskPriority


class TasksMixin:
    """
    Mixin providing task management operations.

    Requires on self:
        - _request(method, endpoint, **kwargs) -> dict
        - _sync_entity(space_id, entity) -> dict
        - get_object(object_id) -> Object
        - get_objects_by_structure(space_id, structure_id) -> list
        - delete_object(space_id, object_id) -> bool
    """

    def get_tasks(
        self,
        space_id: str,
        status: TaskStatus = None,
        priority: TaskPriority = None,
    ) -> List[Task]:
        """
        Get all tasks in a space, optionally filtered by status or priority.
        """
        objects = self.get_objects_by_structure(space_id, "RootTask")
        tasks = [Task.from_object(obj) for obj in objects]

        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]

        return tasks

    def get_pending_tasks(self, space_id: str) -> List[Task]:
        """Get all non-completed tasks in a space."""
        tasks = self.get_tasks(space_id)
        return [t for t in tasks if not t.is_completed()]

    def get_overdue_tasks(self, space_id: str) -> List[Task]:
        """Get all overdue tasks (past due date and not completed)."""
        tasks = self.get_tasks(space_id)
        return [t for t in tasks if t.is_overdue()]

    def get_tasks_due_today(self, space_id: str) -> List[Task]:
        """Get all tasks due today."""
        tasks = self.get_tasks(space_id)
        return [t for t in tasks if t.is_due_today()]

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a single task by ID."""
        obj = self.get_object(task_id)
        if not obj or obj.structure_id != "RootTask":
            return None
        return Task.from_object(obj)

    def create_task(
        self,
        space_id: str,
        title: str,
        due_date: str = None,
        priority: TaskPriority = None,
        notes: str = None,
        tags: List[str] = None,
    ) -> Task:
        """Create a new task."""
        import uuid
        from datetime import datetime, timezone

        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        properties = {
            "title": {"val": title},
            "status": {"val": ["not-started"]},
            "icon": {},
            "tags": {"val": tags or []},
            "RootTask_notes": {"val": "RootTask_notes"},
        }

        if priority:
            properties["priority"] = {"val": [priority.value]}

        if due_date:
            if "T" in due_date:
                date_str = due_date if due_date.endswith("Z") else due_date + "Z"
            else:
                date_str = f"{due_date}T00:00:00.000Z"
            properties["date"] = {
                "val": {
                    "startTime": date_str,
                    "dateResolution": "day",
                }
            }

        blocks = {}
        if notes:
            block_id = str(uuid.uuid4())
            token_id = str(uuid.uuid4())
            blocks["RootTask_notes"] = [
                {
                    "id": block_id,
                    "type": "TextBlock",
                    "blocks": [],
                    "hierarchy": {"key": "Base", "val": 0},
                    "tokens": [
                        {
                            "type": "TextToken",
                            "id": token_id,
                            "text": notes,
                            "style": {"bold": False, "italic": False},
                        }
                    ],
                }
            ]

        entity = {
            "id": task_id,
            "type": "RootTask",
            "structureId": "RootTask",
            "createdAt": now,
            "lastUpdated": now,
            "loadingState": "full",
            "deleteRequested": False,
            "properties": properties,
            "data": {
                "blocks": blocks,
                "hidePropertySection": False,
            },
            "databases": [],
            "policies": [
                {
                    "name": "write",
                    "principals": [
                        {
                            "name": "SpaceEditor",
                            "config": {"spaceId": space_id},
                        }
                    ],
                    "principalType": "Role",
                }
            ],
            "linkNodes": [],
        }

        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def complete_task(self, space_id: str, task_id: str) -> Task:
        """Mark a task as completed."""
        from datetime import datetime, timezone

        task = self.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        entity = task.raw_data.copy()
        now = datetime.now(timezone.utc)
        now_str = now.isoformat().replace("+00:00", "Z")

        entity["lastUpdated"] = now_str
        entity["properties"]["status"] = {"val": ["done"]}
        entity["properties"]["completed"] = {
            "val": {
                "startTime": now_str,
                "dateResolution": "time",
            }
        }

        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def uncomplete_task(self, space_id: str, task_id: str) -> Task:
        """Mark a completed task as not completed."""
        from datetime import datetime, timezone

        task = self.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        entity = task.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entity["lastUpdated"] = now
        entity["properties"]["status"] = {"val": ["not-started"]}
        if "completed" in entity["properties"]:
            entity["properties"]["completed"] = {}

        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def set_task_priority(
        self, space_id: str, task_id: str, priority: TaskPriority
    ) -> Task:
        """Set task priority."""
        from datetime import datetime, timezone

        task = self.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        entity = task.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entity["lastUpdated"] = now
        entity["properties"]["priority"] = {"val": [priority.value]}

        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def set_task_due_date(
        self, space_id: str, task_id: str, due_date: str
    ) -> Task:
        """Set task due date."""
        from datetime import datetime, timezone

        task = self.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        entity = task.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entity["lastUpdated"] = now

        if "T" in due_date:
            date_str = due_date if due_date.endswith("Z") else due_date + "Z"
        else:
            date_str = f"{due_date}T00:00:00.000Z"

        entity["properties"]["date"] = {
            "val": {
                "startTime": date_str,
                "dateResolution": "day",
            }
        }

        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def update_task(
        self,
        space_id: str,
        task_id: str,
        title: str = None,
        status: TaskStatus = None,
        priority: TaskPriority = None,
        due_date: str = None,
        notes: str = None,
        tags: List[str] = None,
    ) -> Task:
        """Update a task with any combination of fields."""
        import uuid
        from datetime import datetime, timezone

        task = self.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        entity = task.raw_data.copy()
        now = datetime.now(timezone.utc)
        now_str = now.isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now_str

        if title is not None:
            entity["properties"]["title"] = {"val": title}

        if status is not None:
            entity["properties"]["status"] = {"val": [status.value]}
            if status == TaskStatus.DONE:
                entity["properties"]["completed"] = {
                    "val": {
                        "startTime": now_str,
                        "dateResolution": "time",
                    }
                }
            else:
                if "completed" in entity["properties"]:
                    entity["properties"]["completed"] = {}

        if priority is not None:
            entity["properties"]["priority"] = {"val": [priority.value]}

        if due_date is not None:
            if "T" in due_date:
                date_str = due_date if due_date.endswith("Z") else due_date + "Z"
            else:
                date_str = f"{due_date}T00:00:00.000Z"
            entity["properties"]["date"] = {
                "val": {
                    "startTime": date_str,
                    "dateResolution": "day",
                }
            }

        if tags is not None:
            entity["properties"]["tags"] = {"val": tags}

        if notes is not None:
            block_id = str(uuid.uuid4())
            token_id = str(uuid.uuid4())
            entity["data"]["blocks"]["RootTask_notes"] = [
                {
                    "id": block_id,
                    "type": "TextBlock",
                    "blocks": [],
                    "hierarchy": {"key": "Base", "val": 0},
                    "tokens": [
                        {
                            "type": "TextToken",
                            "id": token_id,
                            "text": notes,
                            "style": {"bold": False, "italic": False},
                        }
                    ],
                }
            ]

        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def delete_task(self, space_id: str, task_id: str) -> bool:
        """Delete a task (moves to trash)."""
        return self.delete_object(space_id, task_id)
