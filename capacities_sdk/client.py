"""Main client for Capacities API."""

import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin

import requests

from .exceptions import (
    AuthenticationError,
    CapacitiesError,
    NotFoundError,
    RateLimitError,
    SyncError,
    ValidationError,
)
from .models import GraphNode, Object, Space, Structure, Task, TaskStatus, TaskPriority
from .blocks import markdown_to_blocks, create_link_token, create_entity_block
from .mixins import ObjectsMixin


class CapacitiesClient(ObjectsMixin):
    """
    Client for Capacities internal Portal API.

    This client provides full CRUD access to Capacities data via the
    internal Portal API used by the web app.

    Args:
        auth_token: JWT authentication token (from web app session or API settings)
        app_version: App version string (default: "web-1.57")
        base_url: Portal API base URL
        timeout: Request timeout in seconds
    """

    PORTAL_BASE_URL = "https://portal.capacities.io"
    PUBLIC_API_BASE_URL = "https://api.capacities.io"

    def __init__(
        self,
        auth_token: str,
        app_version: str = "web-1.57",
        base_url: str = None,
        timeout: int = 30,
    ):
        self.auth_token = auth_token
        self.app_version = app_version
        self.base_url = base_url or self.PORTAL_BASE_URL
        self.timeout = timeout
        self._session = requests.Session()
        self._setup_session()

    def _setup_session(self):
        """Configure session headers."""
        # Handle token format - add Bearer prefix if not present
        token = self.auth_token
        if not token.startswith("Bearer "):
            token = f"Bearer {token}"

        self._session.headers.update(
            {
                "auth-token": token,
                "appversion": self.app_version,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        json: Dict[str, Any] = None,
        use_public_api: bool = False,
    ) -> Dict[str, Any]:
        """Make an API request."""
        base = self.PUBLIC_API_BASE_URL if use_public_api else self.base_url
        url = urljoin(base + "/", endpoint.lstrip("/"))

        # For public API, use Authorization header instead of auth-token
        headers = {}
        if use_public_api:
            headers["Authorization"] = self._session.headers.get("auth-token", "")

        try:
            response = self._session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=self.timeout,
                headers=headers if use_public_api else None,
            )
        except requests.RequestException as e:
            raise CapacitiesError(f"Request failed: {e}")

        # Handle errors
        if response.status_code == 401:
            raise AuthenticationError("Invalid or expired authentication token")
        elif response.status_code == 404:
            raise NotFoundError(f"Resource not found: {endpoint}")
        elif response.status_code == 429:
            retry_after = int(response.headers.get("RateLimit-Reset", 60))
            raise RateLimitError(
                f"Rate limit exceeded. Retry after {retry_after}s",
                retry_after=retry_after,
            )
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", response.text)
            except Exception:
                error_msg = response.text
            if "inputValidationFailed" in str(error_msg):
                raise ValidationError(f"Input validation failed: {error_msg}")
            raise CapacitiesError(
                f"API error: {error_msg}", status_code=response.status_code
            )

        # Parse response
        if response.text:
            try:
                return response.json()
            except Exception:
                return {"raw": response.text}
        return {}

    # =========================================================================
    # Graph Traversal
    # =========================================================================

    def trace_graph(
        self,
        start_object_id: str,
        max_depth: int = 3,
        direction: str = "both",
    ) -> List[GraphNode]:
        """
        Trace the object graph starting from a given object.

        Args:
            start_object_id: Starting object UUID
            max_depth: Maximum depth to traverse (1-3 recommended)
            direction: 'outgoing' (links from), 'incoming' (links to), or 'both'

        Returns:
            List of GraphNode instances representing the graph
        """
        if max_depth < 1 or max_depth > 10:
            raise ValueError("max_depth must be between 1 and 10")

        visited: Set[str] = set()
        result: List[GraphNode] = []
        queue: List[tuple] = [(start_object_id, 0, None)]  # (id, depth, parent_id)

        while queue:
            current_id, depth, parent_id = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Fetch the object
            obj = self.get_object(current_id)
            if not obj:
                continue

            # Add to result
            node = GraphNode(object=obj, depth=depth, parent_id=parent_id)
            result.append(node)

            # Don't traverse further if at max depth
            if depth >= max_depth:
                continue

            # Get linked objects (outgoing links)
            if direction in ("outgoing", "both"):
                for link_node in obj.link_nodes:
                    if link_node.target_id and link_node.target_id not in visited:
                        queue.append((link_node.target_id, depth + 1, current_id))

            # For incoming links, we'd need to search all objects
            # This is expensive, so only do it if explicitly requested
            if direction in ("incoming", "both") and depth == 0:
                # Get space_id from the object's raw data if available
                if obj.raw_data and obj.databases:
                    # Find objects that link to this one
                    # This would require fetching all objects and checking their links
                    # For efficiency, we skip this for now
                    pass

        return result

    def get_graph_summary(
        self, start_object_id: str, max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get a summary of the object graph.

        Args:
            start_object_id: Starting object UUID
            max_depth: Maximum depth to traverse

        Returns:
            Dict with graph statistics and structure
        """
        nodes = self.trace_graph(start_object_id, max_depth)

        # Build adjacency list
        adjacency = {}
        for node in nodes:
            adjacency[node.get_id()] = {
                "title": node.get_title(),
                "type": node.object.structure_id,
                "depth": node.depth,
                "links": [ln.target_id for ln in node.object.link_nodes],
            }

        # Count by type
        type_counts = {}
        for node in nodes:
            t = node.object.structure_id
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_nodes": len(nodes),
            "max_depth_reached": max(n.depth for n in nodes) if nodes else 0,
            "type_counts": type_counts,
            "nodes": adjacency,
        }

    # =========================================================================
    # Public API Methods (Official Endpoints)
    # =========================================================================

    def get_spaces(self) -> List[Space]:
        """
        Get all spaces (uses official API).

        Returns:
            List of Space instances
        """
        data = self._request("GET", "/spaces", use_public_api=True)
        spaces = data.get("spaces", [])
        return [Space.from_dict(s) for s in spaces]

    def get_space_info(self, space_id: str) -> Dict[str, Any]:
        """
        Get space structures and collections (uses official API).

        Args:
            space_id: Space UUID

        Returns:
            Dict with structures information
        """
        data = self._request(
            "GET", "/space-info", params={"spaceid": space_id}, use_public_api=True
        )
        return data

    def get_structures(self, space_id: str) -> List[Structure]:
        """
        Get all structures (object types) in a space.

        Args:
            space_id: Space UUID

        Returns:
            List of Structure instances
        """
        data = self.get_space_info(space_id)
        structures = data.get("structures", [])
        return [Structure.from_dict(s) for s in structures]

    def lookup(self, space_id: str, search_term: str) -> List[Dict[str, Any]]:
        """
        Lookup content by title (uses official API).

        Args:
            space_id: Space UUID
            search_term: Title to search for

        Returns:
            List of matching results with id, structureId, title
        """
        data = self._request(
            "POST",
            "/lookup",
            json={"spaceId": space_id, "searchTerm": search_term},
            use_public_api=True,
        )
        return data.get("results", [])

    def save_weblink(
        self,
        space_id: str,
        url: str,
        title: str = None,
        description: str = None,
        tags: List[str] = None,
        md_text: str = None,
    ) -> Dict[str, Any]:
        """
        Save a weblink to a space (uses official API).

        Args:
            space_id: Space UUID
            url: URL to save
            title: Optional custom title
            description: Optional description
            tags: Optional list of tags
            md_text: Optional markdown content

        Returns:
            Created weblink info
        """
        payload = {"spaceId": space_id, "url": url}
        if title:
            payload["titleOverwrite"] = title
        if description:
            payload["descriptionOverwrite"] = description
        if tags:
            payload["tags"] = tags
        if md_text:
            payload["mdText"] = md_text

        return self._request("POST", "/save-weblink", json=payload, use_public_api=True)

    def save_to_daily_note(
        self,
        space_id: str,
        md_text: str,
        no_timestamp: bool = False,
    ) -> None:
        """
        Add text to today's daily note (uses official API).

        Args:
            space_id: Space UUID
            md_text: Markdown text to add
            no_timestamp: If True, no timestamp will be added
        """
        payload = {"spaceId": space_id, "mdText": md_text}
        if no_timestamp:
            payload["noTimeStamp"] = True

        self._request("POST", "/save-to-daily-note", json=payload, use_public_api=True)

    # =========================================================================
    # Sync Operations (Core methods used by mixins)
    # =========================================================================

    def _get_sync_client_id(self) -> str:
        """
        Get or generate a sync client ID.

        The sync client ID should be consistent per client session.
        """
        import uuid
        if not hasattr(self, "_sync_client_id"):
            self._sync_client_id = str(uuid.uuid4())
        return self._sync_client_id

    def _sync_entity(
        self, space_id: str, entity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync an entity to the server.

        Args:
            space_id: Space UUID
            entity: Full entity dict

        Returns:
            Sync result with status
        """
        payload = {
            "syncClientId": self._get_sync_client_id(),
            "elements": [
                {
                    "spaceId": space_id,
                    "content": entity,
                }
            ],
        }

        data = self._request("POST", "/content/syncing", json=payload)

        results = data.get("componentReturnObjects", [])
        if results and results[0].get("status") == "success":
            return {
                "success": True,
                "id": results[0].get("id"),
                "syncTime": results[0].get("syncTime"),
            }
        else:
            raise SyncError(f"Sync failed: {data}")

    # =========================================================================
    # Task Operations
    # =========================================================================

    def get_tasks(
        self,
        space_id: str,
        status: TaskStatus = None,
        priority: TaskPriority = None,
    ) -> List[Task]:
        """
        Get all tasks in a space, optionally filtered by status or priority.

        Args:
            space_id: Space UUID
            status: Optional status filter
            priority: Optional priority filter

        Returns:
            List of Task instances
        """
        objects = self.get_objects_by_structure(space_id, "RootTask")
        tasks = [Task.from_object(obj) for obj in objects]

        # Apply filters
        if status:
            tasks = [t for t in tasks if t.status == status]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]

        return tasks

    def get_pending_tasks(self, space_id: str) -> List[Task]:
        """
        Get all non-completed tasks in a space.

        Args:
            space_id: Space UUID

        Returns:
            List of pending Task instances
        """
        tasks = self.get_tasks(space_id)
        return [t for t in tasks if not t.is_completed()]

    def get_overdue_tasks(self, space_id: str) -> List[Task]:
        """
        Get all overdue tasks (past due date and not completed).

        Args:
            space_id: Space UUID

        Returns:
            List of overdue Task instances
        """
        tasks = self.get_tasks(space_id)
        return [t for t in tasks if t.is_overdue()]

    def get_tasks_due_today(self, space_id: str) -> List[Task]:
        """
        Get all tasks due today.

        Args:
            space_id: Space UUID

        Returns:
            List of Task instances due today
        """
        tasks = self.get_tasks(space_id)
        return [t for t in tasks if t.is_due_today()]

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a single task by ID.

        Args:
            task_id: Task UUID

        Returns:
            Task instance or None if not found
        """
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
        """
        Create a new task.

        Args:
            space_id: Space UUID
            title: Task title
            due_date: Optional due date (ISO format string, e.g., "2025-01-15")
            priority: Optional priority (high, medium, low)
            notes: Optional notes content
            tags: Optional list of tag IDs

        Returns:
            Created Task instance
        """
        import uuid
        from datetime import datetime, timezone

        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Build properties
        properties = {
            "title": {"val": title},
            "status": {"val": ["not-started"]},
            "icon": {},
            "tags": {"val": tags or []},
            "RootTask_notes": {"val": "RootTask_notes"},
        }

        # Add priority if specified
        if priority:
            properties["priority"] = {"val": [priority.value]}

        # Add due date if specified
        if due_date:
            # Parse the date string and format for API
            if "T" in due_date:
                # Full datetime
                date_str = due_date if due_date.endswith("Z") else due_date + "Z"
            else:
                # Date only - add time component
                date_str = f"{due_date}T00:00:00.000Z"
            properties["date"] = {
                "val": {
                    "startTime": date_str,
                    "dateResolution": "day",
                }
            }

        # Build notes blocks if provided
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

        # Build the full entity
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

        # Sync to server
        result = self._sync_entity(space_id, entity)

        # Fetch and return the created task
        return self.get_task(result["id"])

    def complete_task(self, space_id: str, task_id: str) -> Task:
        """
        Mark a task as completed.

        Args:
            space_id: Space UUID
            task_id: Task UUID

        Returns:
            Updated Task instance
        """
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

        # Sync to server
        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def uncomplete_task(self, space_id: str, task_id: str) -> Task:
        """
        Mark a completed task as not completed.

        Args:
            space_id: Space UUID
            task_id: Task UUID

        Returns:
            Updated Task instance
        """
        from datetime import datetime, timezone

        task = self.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        entity = task.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entity["lastUpdated"] = now
        entity["properties"]["status"] = {"val": ["not-started"]}
        # Remove completed timestamp
        if "completed" in entity["properties"]:
            entity["properties"]["completed"] = {}

        # Sync to server
        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def set_task_priority(
        self, space_id: str, task_id: str, priority: TaskPriority
    ) -> Task:
        """
        Set task priority.

        Args:
            space_id: Space UUID
            task_id: Task UUID
            priority: New priority (high, medium, low)

        Returns:
            Updated Task instance
        """
        from datetime import datetime, timezone

        task = self.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        entity = task.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entity["lastUpdated"] = now
        entity["properties"]["priority"] = {"val": [priority.value]}

        # Sync to server
        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def set_task_due_date(
        self, space_id: str, task_id: str, due_date: str
    ) -> Task:
        """
        Set task due date.

        Args:
            space_id: Space UUID
            task_id: Task UUID
            due_date: Due date (ISO format string, e.g., "2025-01-15")

        Returns:
            Updated Task instance
        """
        from datetime import datetime, timezone

        task = self.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        entity = task.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        entity["lastUpdated"] = now

        # Format due date
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

        # Sync to server
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
        """
        Update a task with any combination of fields.

        Args:
            space_id: Space UUID
            task_id: Task UUID
            title: New title (optional)
            status: New status (optional)
            priority: New priority (optional)
            due_date: New due date as ISO string (optional)
            notes: New notes content (optional, replaces existing)
            tags: New tags list (optional)

        Returns:
            Updated Task instance
        """
        import uuid
        from datetime import datetime, timezone

        task = self.get_task(task_id)
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        entity = task.raw_data.copy()
        now = datetime.now(timezone.utc)
        now_str = now.isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now_str

        # Update title
        if title is not None:
            entity["properties"]["title"] = {"val": title}

        # Update status
        if status is not None:
            entity["properties"]["status"] = {"val": [status.value]}
            # If completing, add completion timestamp
            if status == TaskStatus.DONE:
                entity["properties"]["completed"] = {
                    "val": {
                        "startTime": now_str,
                        "dateResolution": "time",
                    }
                }
            else:
                # Remove completion timestamp
                if "completed" in entity["properties"]:
                    entity["properties"]["completed"] = {}

        # Update priority
        if priority is not None:
            entity["properties"]["priority"] = {"val": [priority.value]}

        # Update due date
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

        # Update tags
        if tags is not None:
            entity["properties"]["tags"] = {"val": tags}

        # Update notes
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

        # Sync to server
        result = self._sync_entity(space_id, entity)
        return self.get_task(result["id"])

    def delete_task(self, space_id: str, task_id: str) -> bool:
        """
        Delete a task (moves to trash).

        Args:
            space_id: Space UUID
            task_id: Task UUID

        Returns:
            True if deletion was successful
        """
        return self.delete_object(space_id, task_id)

    # =========================================================================
    # Collection Operations
    # =========================================================================

    def add_to_collection(
        self, space_id: str, object_id: str, collection_id: str
    ) -> Object:
        """
        Add an object to a collection (database).

        Args:
            space_id: Space UUID
            object_id: Object UUID to add
            collection_id: Collection UUID to add to

        Returns:
            Updated Object instance
        """
        import uuid
        from datetime import datetime, timezone

        obj = self.get_object(object_id)
        if not obj:
            raise NotFoundError(f"Object not found: {object_id}")

        entity = obj.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now

        # Check if already in collection
        databases = entity.get("databases", [])
        for db in databases:
            if db.get("id") == collection_id:
                # Already in collection
                return obj

        # Add to collection
        link_id = str(uuid.uuid4())
        databases.append({
            "id": collection_id,
            "link": {
                "id": link_id,
                "type": "Database",
                "createdAt": now,
                "data": {"toStructureId": "RootDatabase"},
                "policies": []
            }
        })
        entity["databases"] = databases

        # Sync to server
        result = self._sync_entity(space_id, entity)
        return self.get_object(result["id"])

    def remove_from_collection(
        self, space_id: str, object_id: str, collection_id: str
    ) -> Object:
        """
        Remove an object from a collection (database).

        Args:
            space_id: Space UUID
            object_id: Object UUID to remove
            collection_id: Collection UUID to remove from

        Returns:
            Updated Object instance
        """
        from datetime import datetime, timezone

        obj = self.get_object(object_id)
        if not obj:
            raise NotFoundError(f"Object not found: {object_id}")

        entity = obj.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now

        # Remove from databases array
        databases = entity.get("databases", [])
        entity["databases"] = [db for db in databases if db.get("id") != collection_id]

        # Sync to server
        result = self._sync_entity(space_id, entity)
        return self.get_object(result["id"])

    def get_object_collections(self, object_id: str) -> List[str]:
        """
        Get list of collection IDs an object belongs to.

        Args:
            object_id: Object UUID

        Returns:
            List of collection UUIDs
        """
        obj = self.get_object(object_id)
        if not obj:
            return []

        databases = obj.raw_data.get("databases", [])
        return [db.get("id") for db in databases if db.get("id")]

    def get_collection_objects(
        self, space_id: str, collection_id: str
    ) -> List[Object]:
        """
        Get all objects in a collection.

        Args:
            space_id: Space UUID
            collection_id: Collection UUID

        Returns:
            List of Object instances in the collection
        """
        all_objects = self.get_all_objects(space_id)
        return [
            obj for obj in all_objects
            if collection_id in [
                db.get("id") for db in obj.raw_data.get("databases", [])
            ]
        ]

    # =========================================================================
    # Full-Text Search
    # =========================================================================

    def search_content(
        self,
        space_id: str,
        query: str,
        limit: int = 50,
    ) -> List[Object]:
        """
        Full-text search across all content in a space.

        Searches object content, not just titles. More powerful than lookup.

        Args:
            space_id: Space UUID
            query: Search query string
            limit: Maximum results to return (default 50)

        Returns:
            List of matching Object instances
        """
        try:
            data = self._request(
                "POST",
                "/resources/search",
                json={
                    "spaceId": space_id,
                    "query": query,
                    "limit": limit,
                }
            )

            # Extract object IDs from results
            results = data.get("results", data.get("items", []))
            if not results:
                return []

            # Results might be objects or just IDs
            if isinstance(results[0], dict):
                object_ids = [r.get("id", r.get("entityId")) for r in results]
            else:
                object_ids = results

            object_ids = [oid for oid in object_ids if oid][:limit]

            if not object_ids:
                return []

            return self.get_objects_by_ids(object_ids)

        except CapacitiesError:
            # If endpoint doesn't work, fall back to client-side search
            return self._search_content_fallback(space_id, query, limit)

    def _search_content_fallback(
        self, space_id: str, query: str, limit: int
    ) -> List[Object]:
        """
        Fallback content search by fetching all objects and searching locally.

        Used if /resources/search endpoint is not available.
        """
        query_lower = query.lower()
        all_objects = self.get_all_objects(space_id)
        matches = []

        for obj in all_objects:
            # Search in title
            if query_lower in obj.title.lower():
                matches.append(obj)
                continue

            # Search in description
            if obj.description and query_lower in obj.description.lower():
                matches.append(obj)
                continue

            # Search in content
            content = obj.get_content_text()
            if content and query_lower in content.lower():
                matches.append(obj)
                continue

            if len(matches) >= limit:
                break

        return matches[:limit]

    # =========================================================================
    # Link Operations
    # =========================================================================

    def get_links(self, object_id: str) -> List[Dict[str, Any]]:
        """
        Get all links (references to other objects) from an object's content.

        Args:
            object_id: Object UUID

        Returns:
            List of link info dicts with target_id, display_text, etc.
        """
        obj = self.get_object(object_id)
        if not obj:
            return []

        links = obj.get_links()
        return [
            {
                "id": link.id,
                "target_id": link.target_id,
                "target_structure_id": link.target_structure_id,
                "display_text": link.display_text,
                "type": link.type,
            }
            for link in links
        ]

    def get_backlinks(self, space_id: str, object_id: str) -> List[Object]:
        """
        Get all objects that link to a given object.

        Args:
            space_id: Space UUID
            object_id: Object UUID to find links to

        Returns:
            List of Object instances that contain links to the target
        """
        all_objects = self.get_all_objects(space_id)
        backlinks = []

        for obj in all_objects:
            if obj.id == object_id:
                continue

            linked_ids = obj.get_linked_object_ids()
            if object_id in linked_ids:
                backlinks.append(obj)

        return backlinks

    def add_link(
        self,
        space_id: str,
        source_object_id: str,
        target_object_id: str,
        display_text: str = None,
        as_block: bool = False,
    ) -> Object:
        """
        Add a link from one object to another.

        Creates either an inline LinkToken or an EntityBlock in the source
        object's content that references the target object.

        Args:
            space_id: Space UUID
            source_object_id: Object UUID to add the link to
            target_object_id: Object UUID to link to
            display_text: Text to display for inline links (defaults to target title)
            as_block: If True, creates an EntityBlock; if False, adds inline LinkToken

        Returns:
            Updated source Object instance
        """
        import uuid as uuid_module
        from datetime import datetime, timezone

        # Get source object
        source = self.get_object(source_object_id)
        if not source:
            raise NotFoundError(f"Source object not found: {source_object_id}")

        # Get target object to get structure and title
        target = self.get_object(target_object_id)
        if not target:
            raise NotFoundError(f"Target object not found: {target_object_id}")

        entity = source.raw_data.copy()
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entity["lastUpdated"] = now

        # Find or create content block area
        blocks_data = entity.get("data", {}).get("blocks", {})
        content_property_id = None

        # Find existing content property
        for prop_id, block_list in blocks_data.items():
            if block_list:
                content_property_id = prop_id
                break

        if not content_property_id:
            content_property_id = str(uuid_module.uuid4())
            entity["properties"][content_property_id] = {"val": content_property_id}
            entity["data"]["blocks"][content_property_id] = []

        if as_block:
            # Add EntityBlock
            entity_block = create_entity_block(
                target_id=target_object_id,
                target_structure_id=target.structure_id,
            )
            entity["data"]["blocks"][content_property_id].append(entity_block)
        else:
            # Add inline LinkToken to a TextBlock
            link_text = display_text or target.title
            link_token = create_link_token(
                target_id=target_object_id,
                display_text=link_text,
                target_structure_id=target.structure_id,
            )

            # Find last TextBlock or create new one
            blocks = entity["data"]["blocks"][content_property_id]
            text_block = None

            for block in reversed(blocks):
                if block.get("type") == "TextBlock":
                    text_block = block
                    break

            if text_block:
                # Add link token to existing block
                if not text_block.get("tokens"):
                    text_block["tokens"] = []
                # Add space before link if there are existing tokens
                if text_block["tokens"]:
                    text_block["tokens"].append({
                        "type": "TextToken",
                        "id": str(uuid_module.uuid4()),
                        "text": " ",
                        "style": {"bold": False, "italic": False}
                    })
                text_block["tokens"].append(link_token)
            else:
                # Create new TextBlock with the link
                new_block = {
                    "id": str(uuid_module.uuid4()),
                    "type": "TextBlock",
                    "blocks": [],
                    "hierarchy": {"key": "Base", "val": 0},
                    "tokens": [link_token]
                }
                entity["data"]["blocks"][content_property_id].append(new_block)

        # Sync to server
        result = self._sync_entity(space_id, entity)
        return self.get_object(result["id"])

    def get_linked_objects(
        self, object_id: str
    ) -> List[Object]:
        """
        Get all objects that a given object links to.

        Args:
            object_id: Source object UUID

        Returns:
            List of Object instances that are linked from the source
        """
        obj = self.get_object(object_id)
        if not obj:
            return []

        linked_ids = obj.get_linked_object_ids()
        if not linked_ids:
            return []

        return self.get_objects_by_ids(linked_ids)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def _sync_entities(
        self, space_id: str, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Sync multiple entities to the server in a single request.

        Args:
            space_id: Space UUID
            entities: List of full entity dicts

        Returns:
            List of sync results with status for each entity
        """
        if not entities:
            return []

        payload = {
            "syncClientId": self._get_sync_client_id(),
            "elements": [
                {
                    "spaceId": space_id,
                    "content": entity,
                }
                for entity in entities
            ],
        }

        data = self._request("POST", "/content/syncing", json=payload)

        results = data.get("componentReturnObjects", [])
        return results

    def bulk_create(
        self,
        space_id: str,
        objects: List[Dict[str, Any]],
        batch_size: int = 50,
    ) -> List[Object]:
        """
        Create multiple objects in bulk.

        Args:
            space_id: Space UUID
            objects: List of object specs with keys: structure_id, title, content (optional),
                     description (optional), tags (optional)
            batch_size: Number of objects per batch (default 50)

        Returns:
            List of created Object instances
        """
        import uuid
        from datetime import datetime, timezone

        all_created_ids = []

        for batch_start in range(0, len(objects), batch_size):
            batch = objects[batch_start:batch_start + batch_size]
            entities = []

            for obj_spec in batch:
                object_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

                # Build properties
                obj_properties = {
                    "title": {"val": obj_spec["title"]},
                    "description": {"val": obj_spec.get("description", "")},
                    "icon": {},
                    "tags": {"val": obj_spec.get("tags", [])},
                }

                # Build content blocks
                content_property_id = str(uuid.uuid4())
                blocks = {}
                if obj_spec.get("content"):
                    parsed_blocks = markdown_to_blocks(obj_spec["content"])
                    if parsed_blocks:
                        blocks[content_property_id] = parsed_blocks
                        obj_properties[content_property_id] = {"val": content_property_id}

                entity = {
                    "id": object_id,
                    "type": "RootEntity",
                    "structureId": obj_spec["structure_id"],
                    "createdAt": now,
                    "lastUpdated": now,
                    "loadingState": "full",
                    "deleteRequested": False,
                    "properties": obj_properties,
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
                entities.append(entity)

            # Sync batch
            results = self._sync_entities(space_id, entities)
            for result in results:
                if result.get("status") == "success":
                    all_created_ids.append(result.get("id"))

            # Small delay between batches
            if batch_start + batch_size < len(objects):
                time.sleep(0.1)

        # Fetch and return created objects
        return self.get_objects_by_ids(all_created_ids)

    def bulk_update(
        self,
        space_id: str,
        updates: List[Dict[str, Any]],
        batch_size: int = 50,
    ) -> List[Object]:
        """
        Update multiple objects in bulk.

        Args:
            space_id: Space UUID
            updates: List of update specs with keys: object_id, and optional:
                     title, content, description, tags
            batch_size: Number of objects per batch (default 50)

        Returns:
            List of updated Object instances
        """
        import uuid as uuid_module
        from datetime import datetime, timezone

        all_updated_ids = []

        for batch_start in range(0, len(updates), batch_size):
            batch = updates[batch_start:batch_start + batch_size]

            # Fetch current objects
            object_ids = [u["object_id"] for u in batch]
            current_objects = self.get_objects_by_ids(object_ids)
            obj_map = {obj.id: obj for obj in current_objects}

            entities = []
            for update_spec in batch:
                obj_id = update_spec["object_id"]
                obj = obj_map.get(obj_id)
                if not obj:
                    continue

                entity = obj.raw_data.copy()
                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                entity["lastUpdated"] = now

                # Apply updates
                if "title" in update_spec:
                    entity["properties"]["title"] = {"val": update_spec["title"]}
                if "description" in update_spec:
                    entity["properties"]["description"] = {"val": update_spec["description"]}
                if "tags" in update_spec:
                    entity["properties"]["tags"] = {"val": update_spec["tags"]}

                # Update content if provided
                if "content" in update_spec:
                    content_property_id = None
                    for prop_id, blocks in entity.get("data", {}).get("blocks", {}).items():
                        if blocks:
                            content_property_id = prop_id
                            break

                    if not content_property_id:
                        content_property_id = str(uuid_module.uuid4())
                        entity["properties"][content_property_id] = {"val": content_property_id}

                    parsed_blocks = markdown_to_blocks(update_spec["content"])
                    entity["data"]["blocks"][content_property_id] = parsed_blocks

                entities.append(entity)

            # Sync batch
            results = self._sync_entities(space_id, entities)
            for result in results:
                if result.get("status") == "success":
                    all_updated_ids.append(result.get("id"))

            # Small delay between batches
            if batch_start + batch_size < len(updates):
                time.sleep(0.1)

        # Fetch and return updated objects
        return self.get_objects_by_ids(all_updated_ids)

    def bulk_delete(
        self,
        space_id: str,
        object_ids: List[str],
        batch_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Delete multiple objects in bulk (moves to trash).

        Args:
            space_id: Space UUID
            object_ids: List of object UUIDs to delete
            batch_size: Number of objects per batch (default 50)

        Returns:
            Dict with success_count, failed_count, and failed_ids
        """
        from datetime import datetime, timezone

        success_count = 0
        failed_ids = []

        for batch_start in range(0, len(object_ids), batch_size):
            batch_ids = object_ids[batch_start:batch_start + batch_size]

            # Fetch current objects
            current_objects = self.get_objects_by_ids(batch_ids)
            obj_map = {obj.id: obj for obj in current_objects}

            entities = []
            batch_obj_ids = []
            for obj_id in batch_ids:
                obj = obj_map.get(obj_id)
                if not obj:
                    failed_ids.append(obj_id)
                    continue

                entity = obj.raw_data.copy()
                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                entity["lastUpdated"] = now
                entity["deleteRequested"] = True
                entities.append(entity)
                batch_obj_ids.append(obj_id)

            # Sync batch
            if entities:
                results = self._sync_entities(space_id, entities)
                for i, result in enumerate(results):
                    if result.get("status") == "success":
                        success_count += 1
                    else:
                        if i < len(batch_obj_ids):
                            failed_ids.append(batch_obj_ids[i])

            # Small delay between batches
            if batch_start + batch_size < len(object_ids):
                time.sleep(0.1)

        return {
            "success_count": success_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids,
        }

    def bulk_restore(
        self,
        space_id: str,
        object_ids: List[str],
        batch_size: int = 50,
    ) -> List[Object]:
        """
        Restore multiple deleted objects from trash in bulk.

        Args:
            space_id: Space UUID
            object_ids: List of object UUIDs to restore
            batch_size: Number of objects per batch (default 50)

        Returns:
            List of restored Object instances
        """
        from datetime import datetime, timezone

        restored_ids = []

        for batch_start in range(0, len(object_ids), batch_size):
            batch_ids = object_ids[batch_start:batch_start + batch_size]

            # Fetch current objects
            current_objects = self.get_objects_by_ids(batch_ids)

            entities = []
            for obj in current_objects:
                entity = obj.raw_data.copy()
                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                entity["lastUpdated"] = now
                entity["deleteRequested"] = False
                entities.append(entity)

            # Sync batch
            if entities:
                results = self._sync_entities(space_id, entities)
                for result in results:
                    if result.get("status") == "success":
                        restored_ids.append(result.get("id"))

            # Small delay between batches
            if batch_start + batch_size < len(object_ids):
                time.sleep(0.1)

        return self.get_objects_by_ids(restored_ids)

    # =========================================================================
    # Export/Import Operations
    # =========================================================================

    def export_space_json(
        self,
        space_id: str,
        include_content: bool = True,
    ) -> Dict[str, Any]:
        """
        Export all objects in a space to JSON format.

        Creates a complete backup that can be used for import.

        Args:
            space_id: Space UUID
            include_content: Include full content (default True)

        Returns:
            Dict with space_id, exported_at, objects list, and metadata
        """
        from datetime import datetime, timezone

        objects = self.get_all_objects(space_id)

        exported_objects = []
        for obj in objects:
            if include_content:
                exported_objects.append(obj.raw_data)
            else:
                # Minimal export - just metadata
                exported_objects.append({
                    "id": obj.id,
                    "structureId": obj.structure_id,
                    "properties": {
                        "title": {"val": obj.title},
                        "description": {"val": obj.description or ""},
                        "tags": {"val": obj.tags},
                    },
                    "createdAt": obj.raw_data.get("createdAt"),
                    "lastUpdated": obj.raw_data.get("lastUpdated"),
                })

        # Get structures for reference (may fail if public API token unavailable)
        structure_info = []
        try:
            structures = self.get_structures(space_id)
            structure_info = [
                {
                    "id": s.id,
                    "title": s.title,
                    "pluralName": s.plural_name,
                }
                for s in structures
            ]
        except Exception:
            # Structure info is optional - extract unique structure IDs from objects instead
            structure_ids = set(obj.structure_id for obj in objects)
            structure_info = [{"id": sid, "title": sid, "pluralName": sid} for sid in structure_ids]

        return {
            "version": "1.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "space_id": space_id,
            "object_count": len(exported_objects),
            "structures": structure_info,
            "objects": exported_objects,
        }

    def export_objects_to_markdown(
        self,
        space_id: str,
        object_ids: List[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Export objects as markdown files.

        Args:
            space_id: Space UUID
            object_ids: Optional list of specific object IDs (default: all objects)

        Returns:
            List of dicts with filename, title, content, metadata for each object
        """
        import re

        if object_ids:
            objects = self.get_objects_by_ids(object_ids)
        else:
            objects = self.get_all_objects(space_id)

        exports = []
        for obj in objects:
            # Generate safe filename
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', obj.title)
            safe_title = safe_title[:100]  # Limit length
            filename = f"{safe_title}.md"

            # Build markdown content
            md_lines = [f"# {obj.title}"]

            if obj.description:
                md_lines.append("")
                md_lines.append(f"> {obj.description}")

            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

            # Add metadata as YAML frontmatter comment
            md_lines.append(f"<!-- ")
            md_lines.append(f"id: {obj.id}")
            md_lines.append(f"type: {obj.structure_id}")
            if obj.created_at:
                md_lines.append(f"created: {obj.created_at.isoformat()}")
            if obj.last_updated:
                md_lines.append(f"updated: {obj.last_updated.isoformat()}")
            if obj.tags:
                md_lines.append(f"tags: {', '.join(obj.tags)}")
            md_lines.append(" -->")
            md_lines.append("")

            # Add content
            content = obj.get_content_text()
            if content:
                md_lines.append(content)

            # Add links section
            linked_ids = obj.get_linked_object_ids()
            if linked_ids:
                md_lines.append("")
                md_lines.append("## Links")
                md_lines.append("")
                for link_id in linked_ids:
                    md_lines.append(f"- [[{link_id}]]")

            exports.append({
                "filename": filename,
                "title": obj.title,
                "id": obj.id,
                "structure_id": obj.structure_id,
                "content": "\n".join(md_lines),
            })

        return exports

    def import_from_json(
        self,
        space_id: str,
        export_data: Dict[str, Any],
        create_new_ids: bool = True,
        skip_existing: bool = True,
    ) -> Dict[str, Any]:
        """
        Import objects from a JSON export.

        Args:
            space_id: Space UUID to import into
            export_data: Export data from export_space_json
            create_new_ids: Generate new IDs for imported objects (default True)
            skip_existing: Skip objects that already exist by title (default True)

        Returns:
            Dict with imported_count, skipped_count, failed_count, and details
        """
        import uuid as uuid_module
        from datetime import datetime, timezone

        objects_to_import = export_data.get("objects", [])
        if not objects_to_import:
            return {
                "imported_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "details": [],
            }

        # Get existing objects if skip_existing
        existing_titles = set()
        if skip_existing:
            existing_objects = self.get_all_objects(space_id)
            existing_titles = {obj.title.lower() for obj in existing_objects}

        imported_count = 0
        skipped_count = 0
        failed_count = 0
        details = []

        # Create ID mapping for references
        id_mapping = {}

        entities_to_create = []
        for obj_data in objects_to_import:
            title = obj_data.get("properties", {}).get("title", {}).get("val", "Untitled")

            # Check if exists
            if skip_existing and title.lower() in existing_titles:
                skipped_count += 1
                details.append({
                    "title": title,
                    "status": "skipped",
                    "reason": "exists",
                })
                continue

            # Create entity
            entity = obj_data.copy()
            old_id = entity.get("id")

            if create_new_ids:
                new_id = str(uuid_module.uuid4())
                id_mapping[old_id] = new_id
                entity["id"] = new_id

            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            entity["lastUpdated"] = now
            entity["deleteRequested"] = False

            # Update policies for new space
            entity["policies"] = [
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
            ]

            entities_to_create.append((title, entity))

        # Batch create
        batch_size = 50
        for batch_start in range(0, len(entities_to_create), batch_size):
            batch = entities_to_create[batch_start:batch_start + batch_size]
            entities = [e[1] for e in batch]
            titles = [e[0] for e in batch]

            try:
                results = self._sync_entities(space_id, entities)
                for i, result in enumerate(results):
                    if result.get("status") == "success":
                        imported_count += 1
                        details.append({
                            "title": titles[i] if i < len(titles) else "Unknown",
                            "status": "imported",
                            "id": result.get("id"),
                        })
                    else:
                        failed_count += 1
                        details.append({
                            "title": titles[i] if i < len(titles) else "Unknown",
                            "status": "failed",
                            "reason": str(result),
                        })
            except Exception as e:
                # If batch fails, mark all as failed
                for title in titles:
                    failed_count += 1
                    details.append({
                        "title": title,
                        "status": "failed",
                        "reason": str(e),
                    })

            # Delay between batches
            if batch_start + batch_size < len(entities_to_create):
                time.sleep(0.2)

        return {
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "id_mapping": id_mapping if create_new_ids else {},
            "details": details,
        }

    def clone_objects(
        self,
        space_id: str,
        object_ids: List[str],
        title_prefix: str = "Copy of ",
    ) -> List[Object]:
        """
        Clone existing objects with new IDs.

        Args:
            space_id: Space UUID
            object_ids: List of object IDs to clone
            title_prefix: Prefix for cloned object titles (default "Copy of ")

        Returns:
            List of cloned Object instances
        """
        import uuid as uuid_module
        from datetime import datetime, timezone

        objects = self.get_objects_by_ids(object_ids)
        if not objects:
            return []

        entities = []
        for obj in objects:
            entity = obj.raw_data.copy()
            entity["id"] = str(uuid_module.uuid4())
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            entity["createdAt"] = now
            entity["lastUpdated"] = now
            entity["deleteRequested"] = False

            # Update title
            old_title = entity.get("properties", {}).get("title", {}).get("val", "")
            entity["properties"]["title"] = {"val": f"{title_prefix}{old_title}"}

            # Update policies for space
            entity["policies"] = [
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
            ]

            entities.append(entity)

        # Sync all at once
        results = self._sync_entities(space_id, entities)
        created_ids = [
            r.get("id") for r in results
            if r.get("status") == "success"
        ]

        return self.get_objects_by_ids(created_ids)
