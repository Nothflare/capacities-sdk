"""
Capacities SDK - Unofficial Python SDK for Capacities.io

Full CRUD operations via the internal Portal API.

Usage:
    from capacities_sdk import CapacitiesClient

    client = CapacitiesClient(auth_token="your-jwt-token")

    # List all objects in a space
    objects = client.list_objects(space_id="your-space-id")

    # Get a specific object
    obj = client.get_object(object_id="object-uuid")

    # Search
    results = client.search(space_id, query="PKM")
"""

from .client import CapacitiesClient
from .models import (
    Space,
    Structure,
    Object,
    Block,
    TextBlock,
    CodeBlock,
    HeadingBlock,
    LinkNode,
    Property,
    Task,
    TaskStatus,
    TaskPriority,
)
from .blocks import (
    markdown_to_blocks,
    blocks_to_markdown,
    create_text_block,
    create_heading_block,
    create_code_block,
    create_horizontal_line_block,
    create_quote_block,
    create_link_token,
    create_entity_block,
)
from .exceptions import (
    CapacitiesError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ValidationError,
)

__version__ = "0.1.0"
__all__ = [
    "CapacitiesClient",
    "Space",
    "Structure",
    "Object",
    "Block",
    "TextBlock",
    "CodeBlock",
    "HeadingBlock",
    "LinkNode",
    "Property",
    "Task",
    "TaskStatus",
    "TaskPriority",
    # Block utilities
    "markdown_to_blocks",
    "blocks_to_markdown",
    "create_text_block",
    "create_heading_block",
    "create_code_block",
    "create_horizontal_line_block",
    "create_quote_block",
    "create_link_token",
    "create_entity_block",
    # Exceptions
    "CapacitiesError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ValidationError",
]
