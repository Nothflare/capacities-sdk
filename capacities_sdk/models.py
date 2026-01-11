"""Data models for Capacities objects."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class StructureId(str, Enum):
    """Built-in structure IDs in Capacities."""

    SPACE = "RootSpace"
    STRUCTURE = "RootStructure"
    DATABASE = "RootDatabase"  # Collection
    QUERY = "RootQuery"
    PAGE = "RootPage"
    ENTITY = "RootEntity"
    DAILY_NOTE = "RootDailyNote"
    TAG = "RootTag"
    TASK = "RootTask"
    AI_CHAT = "RootAIChat"
    TABLE = "RootSimpleTable"
    IMAGE = "MediaImage"
    PDF = "MediaPDF"
    AUDIO = "MediaAudio"
    VIDEO = "MediaVideo"
    WEBLINK = "MediaWebResource"
    FILE = "MediaFile"
    TWEET = "MediaTweet"


class BlockType(str, Enum):
    """Block types in Capacities content."""

    TEXT = "TextBlock"
    CODE = "CodeBlock"
    HEADING = "HeadingBlock"
    HORIZONTAL_LINE = "HorizontalLineBlock"
    TABLE = "SimpleTableBlock"
    IMAGE = "ImageBlock"
    EMBED = "EmbedBlock"


class TaskStatus(str, Enum):
    """Task status values in Capacities."""

    NOT_STARTED = "not-started"
    NEXT_UP = "next-up"
    DONE = "done"


class TaskPriority(str, Enum):
    """Task priority values in Capacities."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Property:
    """A property value on an object."""

    id: str
    value: Any
    name: Optional[str] = None
    type: Optional[str] = None

    @classmethod
    def from_dict(cls, prop_id: str, data: Dict[str, Any]) -> "Property":
        return cls(
            id=prop_id,
            value=data.get("val"),
            name=data.get("name"),
            type=data.get("type"),
        )


@dataclass
class Block:
    """Base class for content blocks."""

    id: str
    type: str
    blocks: List["Block"] = field(default_factory=list)
    hierarchy: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Block":
        block_type = data.get("type", "")

        if block_type == BlockType.TEXT.value:
            return TextBlock.from_dict(data)
        elif block_type == BlockType.CODE.value:
            return CodeBlock.from_dict(data)
        elif block_type == BlockType.HEADING.value:
            return HeadingBlock.from_dict(data)
        else:
            return cls(
                id=data.get("id", ""),
                type=block_type,
                blocks=[cls.from_dict(b) for b in data.get("blocks", [])],
                hierarchy=data.get("hierarchy"),
            )


@dataclass
class TextBlock(Block):
    """A text block with rich text tokens."""

    tokens: List[Any] = field(default_factory=list)
    list_type: Optional[str] = None
    quote_layout: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextBlock":
        return cls(
            id=data.get("id", ""),
            type=BlockType.TEXT.value,
            blocks=[Block.from_dict(b) for b in data.get("blocks", [])],
            hierarchy=data.get("hierarchy"),
            tokens=data.get("tokens", []),
            list_type=data.get("list", {}).get("type") if data.get("list") else None,
            quote_layout=(
                data.get("quote", {}).get("layout") if data.get("quote") else None
            ),
        )

    def to_plain_text(self) -> str:
        """Convert tokens to plain text."""
        text_parts = []
        for token in self.tokens:
            if isinstance(token, str):
                text_parts.append(token)
            elif isinstance(token, dict) and "text" in token:
                text_parts.append(token["text"])
            elif isinstance(token, list):
                for item in token:
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
        return "".join(text_parts)


@dataclass
class CodeBlock(Block):
    """A code block with syntax highlighting."""

    text: str = ""
    language: str = "Text"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeBlock":
        return cls(
            id=data.get("id", ""),
            type=BlockType.CODE.value,
            blocks=[Block.from_dict(b) for b in data.get("blocks", [])],
            hierarchy=data.get("hierarchy"),
            text=data.get("text", ""),
            language=data.get("lang", "Text"),
        )


@dataclass
class HeadingBlock(Block):
    """A heading block with level (1-6)."""

    level: int = 1
    tokens: List[Any] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HeadingBlock":
        return cls(
            id=data.get("id", ""),
            type=BlockType.HEADING.value,
            blocks=[Block.from_dict(b) for b in data.get("blocks", [])],
            hierarchy=data.get("hierarchy"),
            level=data.get("level", 1),
            tokens=data.get("tokens", []),
        )

    def to_plain_text(self) -> str:
        """Convert tokens to plain text."""
        text_parts = []
        for token in self.tokens:
            if isinstance(token, str):
                text_parts.append(token)
            elif isinstance(token, dict) and "text" in token:
                text_parts.append(token["text"])
        return "".join(text_parts)


@dataclass
class LinkNode:
    """
    A link to another object.

    Links in Capacities are stored inline in content blocks as LinkTokens,
    not in the entity-level linkNodes array. This class represents a link
    extracted from content.
    """

    id: str                          # Link relationship ID
    target_id: str                   # Target entity ID
    target_structure_id: str         # Target structure ID
    type: str = "Dependency"         # Link type (usually "Dependency")
    display_text: str = ""           # Display text shown for the link

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LinkNode":
        """Create from legacy linkNodes array format (usually empty)."""
        return cls(
            id=data.get("id", ""),
            target_id=data.get("data", {}).get("toEntityId", ""),
            target_structure_id=data.get("data", {}).get("toStructureId", ""),
            type=data.get("type", "Dependency"),
        )

    @classmethod
    def from_link_token(cls, token: Dict[str, Any]) -> "LinkNode":
        """Create from a LinkToken in content blocks."""
        entity = token.get("entity", {})
        link = entity.get("link", {})
        return cls(
            id=link.get("id", ""),
            target_id=entity.get("id", ""),
            target_structure_id=link.get("data", {}).get("toStructureId", ""),
            type=link.get("type", "Dependency"),
            display_text=token.get("text", ""),
        )


@dataclass
class Object:
    """A Capacities object (entity)."""

    id: str
    type: str
    structure_id: str
    title: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    delete_requested: bool = False
    properties: Dict[str, Property] = field(default_factory=dict)
    blocks: Dict[str, List[Block]] = field(default_factory=dict)
    link_nodes: List[LinkNode] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    databases: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Object":
        """Create an Object from API response data."""
        props_data = data.get("properties", {})
        properties = {}
        for prop_id, prop_val in props_data.items():
            properties[prop_id] = Property.from_dict(prop_id, prop_val)

        # Parse blocks
        blocks_data = data.get("data", {}).get("blocks", {})
        blocks = {}
        for prop_id, block_list in blocks_data.items():
            if isinstance(block_list, list):
                blocks[prop_id] = [Block.from_dict(b) for b in block_list]

        # Parse link nodes
        link_nodes = [LinkNode.from_dict(ln) for ln in data.get("linkNodes", [])]

        # Parse timestamps
        created_at = None
        if data.get("createdAt"):
            try:
                created_at = datetime.fromisoformat(
                    data["createdAt"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        last_updated = None
        if data.get("lastUpdated"):
            try:
                last_updated = datetime.fromisoformat(
                    data["lastUpdated"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        # Get title and description from properties
        title = props_data.get("title", {}).get("val", "Untitled")
        description = props_data.get("description", {}).get("val")
        tags = props_data.get("tags", {}).get("val", [])

        return cls(
            id=data.get("id", ""),
            type=data.get("type", ""),
            structure_id=data.get("structureId", ""),
            title=title,
            description=description,
            created_at=created_at,
            last_updated=last_updated,
            delete_requested=data.get("deleteRequested", False),
            properties=properties,
            blocks=blocks,
            link_nodes=link_nodes,
            tags=tags if isinstance(tags, list) else [],
            databases=data.get("databases", []),
            raw_data=data,
        )

    def get_content_text(self) -> str:
        """Get all text content from blocks as plain text."""
        text_parts = []
        for prop_id, block_list in self.blocks.items():
            for block in block_list:
                if isinstance(block, TextBlock):
                    text = block.to_plain_text()
                    if text:
                        text_parts.append(text)
                elif isinstance(block, CodeBlock):
                    if block.text:
                        text_parts.append(f"```{block.language}\n{block.text}\n```")
        return "\n".join(text_parts)

    def get_linked_object_ids(self) -> List[str]:
        """Get IDs of all linked objects from content."""
        links = self.get_links()
        return [link.target_id for link in links if link.target_id]

    def get_links(self) -> List["LinkNode"]:
        """
        Extract all links from content blocks.

        Links in Capacities are stored as LinkTokens within content blocks,
        not in the entity-level linkNodes array.

        Returns:
            List of LinkNode instances representing inline links
        """
        links = []
        if not self.raw_data:
            return links

        # Search through all blocks in data.blocks
        blocks_data = self.raw_data.get("data", {}).get("blocks", {})
        for prop_id, block_list in blocks_data.items():
            if not isinstance(block_list, list):
                continue
            for block in block_list:
                links.extend(self._extract_links_from_block(block))

        return links

    def _extract_links_from_block(self, block: Dict[str, Any]) -> List["LinkNode"]:
        """Recursively extract links from a block and its children."""
        links = []

        # Check if this is an EntityBlock (block-level link)
        if block.get("type") == "EntityBlock":
            entity = block.get("entity", {})
            if entity.get("id"):
                link = entity.get("link", {})
                links.append(LinkNode(
                    id=link.get("id", ""),
                    target_id=entity.get("id", ""),
                    target_structure_id=link.get("data", {}).get("toStructureId", ""),
                    type=link.get("type", "Dependency"),
                    display_text="",  # EntityBlocks don't have display text
                ))

        # Check tokens for LinkTokens (inline links)
        for token in block.get("tokens", []):
            if isinstance(token, dict) and token.get("type") == "LinkToken":
                links.append(LinkNode.from_link_token(token))

        # Recursively check nested blocks
        for nested in block.get("blocks", []):
            if isinstance(nested, dict):
                links.extend(self._extract_links_from_block(nested))

        return links


@dataclass
class Structure:
    """An object type/structure definition."""

    id: str
    title: str
    plural_name: str
    label_color: str
    property_definitions: List[Dict[str, Any]] = field(default_factory=list)
    collections: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Structure":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            plural_name=data.get("pluralName", ""),
            label_color=data.get("labelColor", ""),
            property_definitions=data.get("propertyDefinitions", []),
            collections=data.get("collections", []),
        )


@dataclass
class Space:
    """A Capacities space (workspace)."""

    id: str
    title: str
    icon: Optional[Dict[str, Any]] = None
    structures: List[Structure] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Space":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            icon=data.get("icon"),
        )


@dataclass
class GraphNode:
    """A node in the object graph for traversal."""

    object: Object
    depth: int
    parent_id: Optional[str] = None

    def get_id(self) -> str:
        return self.object.id

    def get_title(self) -> str:
        return self.object.title


@dataclass
class Task:
    """A Capacities task with status, priority, and due date."""

    id: str
    title: str
    status: TaskStatus = TaskStatus.NOT_STARTED
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_object(cls, obj: Object) -> "Task":
        """Create a Task from an Object with RootTask structure."""
        if obj.structure_id != StructureId.TASK.value:
            raise ValueError(f"Object is not a task: {obj.structure_id}")

        props = obj.raw_data.get("properties", {})

        # Parse status - API returns as array like ["done"]
        status_val = props.get("status", {}).get("val", [])
        if isinstance(status_val, list) and status_val:
            status_str = status_val[0]
        else:
            status_str = "not-started"
        try:
            status = TaskStatus(status_str)
        except ValueError:
            status = TaskStatus.NOT_STARTED

        # Parse priority - API returns as array like ["high"]
        priority_val = props.get("priority", {}).get("val", [])
        priority = None
        if isinstance(priority_val, list) and priority_val:
            try:
                priority = TaskPriority(priority_val[0])
            except ValueError:
                pass

        # Parse due date - API returns as {startTime, dateResolution}
        due_date = None
        date_val = props.get("date", {}).get("val", {})
        if date_val and isinstance(date_val, dict) and date_val.get("startTime"):
            try:
                due_date = datetime.fromisoformat(
                    date_val["startTime"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        # Parse completed timestamp
        completed_at = None
        completed_val = props.get("completed", {}).get("val", {})
        if completed_val and isinstance(completed_val, dict) and completed_val.get("startTime"):
            try:
                completed_at = datetime.fromisoformat(
                    completed_val["startTime"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        # Get notes from blocks
        notes = None
        notes_blocks = obj.raw_data.get("data", {}).get("blocks", {}).get("RootTask_notes", [])
        if notes_blocks:
            # Extract text from TextBlocks
            text_parts = []
            for block in notes_blocks:
                if block.get("type") == "TextBlock":
                    for token in block.get("tokens", []):
                        if isinstance(token, dict) and "text" in token:
                            text_parts.append(token["text"])
            notes = "".join(text_parts) if text_parts else None

        return cls(
            id=obj.id,
            title=obj.title,
            status=status,
            priority=priority,
            due_date=due_date,
            completed_at=completed_at,
            notes=notes,
            tags=obj.tags,
            created_at=obj.created_at,
            last_updated=obj.last_updated,
            raw_data=obj.raw_data,
        )

    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.status == TaskStatus.DONE

    def is_overdue(self) -> bool:
        """Check if task is overdue (has due date in past and not completed)."""
        if self.is_completed() or not self.due_date:
            return False
        return self.due_date < datetime.now(self.due_date.tzinfo)

    def is_due_today(self) -> bool:
        """Check if task is due today."""
        if not self.due_date:
            return False
        today = datetime.now(self.due_date.tzinfo).date()
        return self.due_date.date() == today
