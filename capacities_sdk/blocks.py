"""
Markdown to Blocks parser for Capacities.

Converts markdown content to Capacities block format automatically.
Supports: headings, code blocks, lists, horizontal rules, bold/italic text.
"""

import re
import uuid
from typing import Any, Dict, List, Tuple


def generate_id() -> str:
    """Generate a UUID for blocks and tokens."""
    return str(uuid.uuid4())


def parse_inline_formatting(text: str) -> List[Dict[str, Any]]:
    """
    Parse inline markdown formatting (bold, italic) into tokens.

    Supports:
    - **bold** or __bold__
    - *italic* or _italic_
    - ***bold italic*** or ___bold italic___
    - `inline code` (rendered as bold for now)
    """
    tokens = []

    # Pattern for inline formatting
    # Order matters: bold+italic first, then bold, then italic, then code
    # Use negative lookbehind/lookahead to avoid matching * within ** or _ within __
    patterns = [
        (r'\*\*\*(.+?)\*\*\*', {'bold': True, 'italic': True}),  # ***bold italic***
        (r'___(.+?)___', {'bold': True, 'italic': True}),        # ___bold italic___
        (r'\*\*(.+?)\*\*', {'bold': True, 'italic': False}),     # **bold**
        (r'__(.+?)__', {'bold': True, 'italic': False}),         # __bold__
        (r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', {'bold': False, 'italic': True}),  # *italic* (not **)
        (r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', {'bold': False, 'italic': True}),        # _italic_ (not __)
        (r'`(.+?)`', {'bold': True, 'italic': False}),           # `code` as bold
    ]

    # Simple approach: find all formatted segments and plain text
    # Build a list of (start, end, text, style) tuples
    segments: List[Tuple[int, int, str, Dict[str, bool]]] = []

    for pattern, style in patterns:
        for match in re.finditer(pattern, text):
            # Check if this overlaps with existing segments
            overlaps = False
            for seg in segments:
                if not (match.end() <= seg[0] or match.start() >= seg[1]):
                    overlaps = True
                    break
            if not overlaps:
                segments.append((match.start(), match.end(), match.group(1), style))

    # Sort by position
    segments.sort(key=lambda x: x[0])

    # Build tokens
    pos = 0
    for start, end, content, style in segments:
        # Add plain text before this segment
        if start > pos:
            plain_text = text[pos:start]
            if plain_text:
                tokens.append({
                    "type": "TextToken",
                    "id": generate_id(),
                    "text": plain_text,
                    "style": {"bold": False, "italic": False}
                })
        # Add formatted segment
        tokens.append({
            "type": "TextToken",
            "id": generate_id(),
            "text": content,
            "style": style
        })
        pos = end

    # Add remaining plain text
    if pos < len(text):
        remaining = text[pos:]
        if remaining:
            tokens.append({
                "type": "TextToken",
                "id": generate_id(),
                "text": remaining,
                "style": {"bold": False, "italic": False}
            })

    # If no formatting found, return single plain token
    if not tokens and text:
        tokens.append({
            "type": "TextToken",
            "id": generate_id(),
            "text": text,
            "style": {"bold": False, "italic": False}
        })

    return tokens


def create_text_block(
    text: str,
    list_type: str = None,
    hierarchy_val: int = 0
) -> Dict[str, Any]:
    """
    Create a TextBlock with optional list formatting.

    Args:
        text: The text content (can contain inline markdown)
        list_type: "unordered" for bullets, "ordered" for numbers, None for plain
        hierarchy_val: Indentation level (0 = base)
    """
    block = {
        "id": generate_id(),
        "type": "TextBlock",
        "blocks": [],
        "hierarchy": {"key": "Base", "val": hierarchy_val},
        "tokens": parse_inline_formatting(text)
    }

    if list_type:
        block["list"] = {"type": list_type}

    return block


def create_heading_block(text: str, level: int) -> Dict[str, Any]:
    """
    Create a HeadingBlock.

    Args:
        text: Heading text (can contain inline markdown)
        level: Heading level (1-6)
    """
    return {
        "id": generate_id(),
        "type": "HeadingBlock",
        "level": min(max(level, 1), 6),  # Clamp to 1-6
        "tokens": parse_inline_formatting(text)
    }


def create_code_block(code: str, language: str = "text") -> Dict[str, Any]:
    """
    Create a CodeBlock.

    Args:
        code: The code content
        language: Programming language for syntax highlighting
    """
    return {
        "id": generate_id(),
        "type": "CodeBlock",
        "text": code,
        "lang": language
    }


def create_link_token(
    target_id: str,
    display_text: str,
    target_structure_id: str = "",
) -> Dict[str, Any]:
    """
    Create a LinkToken for inline linking to another entity.

    Args:
        target_id: UUID of the target entity to link to
        display_text: Text to display for the link
        target_structure_id: Structure ID of target (optional, for type hints)

    Returns:
        LinkToken dict ready to be included in a block's tokens array
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "type": "LinkToken",
        "id": generate_id(),
        "text": display_text,
        "entity": {
            "id": target_id,
            "link": {
                "id": generate_id(),
                "type": "Dependency",
                "createdAt": now,
                "data": {
                    "toStructureId": target_structure_id
                } if target_structure_id else {}
            }
        }
    }


def create_entity_block(
    target_id: str,
    target_structure_id: str = "",
) -> Dict[str, Any]:
    """
    Create an EntityBlock for block-level embedding of another entity.

    Args:
        target_id: UUID of the target entity to embed
        target_structure_id: Structure ID of target (optional)

    Returns:
        EntityBlock dict ready to be included in a block list
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "id": generate_id(),
        "type": "EntityBlock",
        "styles": {"contentWidth": "full"},
        "entity": {
            "id": target_id,
            "link": {
                "id": generate_id(),
                "type": "Dependency",
                "createdAt": now,
                "data": {
                    "toStructureId": target_structure_id
                } if target_structure_id else {}
            }
        }
    }


def create_horizontal_line_block() -> Dict[str, Any]:
    """Create a HorizontalLineBlock (divider)."""
    return {
        "id": generate_id(),
        "type": "HorizontalLineBlock"
    }


def create_quote_block(text: str) -> Dict[str, Any]:
    """
    Create a blockquote TextBlock.

    Args:
        text: Quote text (can contain inline markdown)
    """
    return {
        "id": generate_id(),
        "type": "TextBlock",
        "blocks": [],
        "hierarchy": {"key": "Base", "val": 0},
        "tokens": parse_inline_formatting(text),
        "quote": {"layout": "default"}
    }


def markdown_to_blocks(markdown: str) -> List[Dict[str, Any]]:
    """
    Parse markdown content into Capacities blocks.

    Supports:
    - # Headings (levels 1-6)
    - ```language code blocks ```
    - - Bullet lists
    - 1. Numbered lists
    - --- Horizontal rules
    - > Blockquotes
    - **bold**, *italic*, `code` inline formatting
    - Plain paragraphs

    Args:
        markdown: Markdown-formatted string

    Returns:
        List of block dictionaries ready for Capacities API
    """
    blocks = []
    lines = markdown.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Code block (fenced)
        if stripped.startswith('```'):
            # Extract language
            lang = stripped[3:].strip() or "text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            blocks.append(create_code_block('\n'.join(code_lines), lang))
            i += 1  # Skip closing ```
            continue

        # Heading (# to ######)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            blocks.append(create_heading_block(text, level))
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^(-{3,}|_{3,}|\*{3,})$', stripped):
            blocks.append(create_horizontal_line_block())
            i += 1
            continue

        # Blockquote
        if stripped.startswith('>'):
            quote_text = stripped[1:].strip()
            # Collect multi-line quotes
            while i + 1 < len(lines) and lines[i + 1].strip().startswith('>'):
                i += 1
                quote_text += '\n' + lines[i].strip()[1:].strip()
            blocks.append(create_quote_block(quote_text))
            i += 1
            continue

        # Unordered list (-, *, +)
        list_match = re.match(r'^[-*+]\s+(.+)$', stripped)
        if list_match:
            text = list_match.group(1)
            blocks.append(create_text_block(text, list_type="unordered"))
            i += 1
            continue

        # Ordered list (1. 2. etc)
        ordered_match = re.match(r'^\d+\.\s+(.+)$', stripped)
        if ordered_match:
            text = ordered_match.group(1)
            blocks.append(create_text_block(text, list_type="ordered"))
            i += 1
            continue

        # Plain paragraph - collect consecutive non-empty, non-special lines
        para_lines = [stripped]
        while i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            # Stop if next line is empty or starts a new block type
            if not next_line:
                break
            if next_line.startswith(('#', '```', '-', '*', '+', '>', '---', '___', '***')):
                break
            if re.match(r'^\d+\.', next_line):
                break
            para_lines.append(next_line)
            i += 1

        blocks.append(create_text_block(' '.join(para_lines)))
        i += 1

    return blocks


def blocks_to_markdown(blocks: List[Dict[str, Any]]) -> str:
    """
    Convert Capacities blocks back to markdown.

    Args:
        blocks: List of block dictionaries from Capacities

    Returns:
        Markdown-formatted string
    """
    lines = []

    for block in blocks:
        block_type = block.get("type", "")

        if block_type == "HeadingBlock":
            level = block.get("level", 1)
            text = _tokens_to_markdown(block.get("tokens", []))
            lines.append('#' * level + ' ' + text)
            lines.append('')

        elif block_type == "CodeBlock":
            lang = block.get("lang", "")
            code = block.get("text", "")
            lines.append(f'```{lang}')
            lines.append(code)
            lines.append('```')
            lines.append('')

        elif block_type == "HorizontalLineBlock":
            lines.append('---')
            lines.append('')

        elif block_type == "TextBlock":
            text = _tokens_to_markdown(block.get("tokens", []))

            # Check for list
            list_info = block.get("list")
            if list_info:
                list_type = list_info.get("type", "")
                if list_type == "unordered":
                    lines.append(f'- {text}')
                elif list_type == "ordered":
                    lines.append(f'1. {text}')
                else:
                    lines.append(text)
            # Check for quote
            elif block.get("quote"):
                lines.append(f'> {text}')
                lines.append('')
            else:
                lines.append(text)
                lines.append('')

    return '\n'.join(lines).strip()


def _tokens_to_markdown(tokens: List[Any]) -> str:
    """Convert tokens back to markdown text with formatting."""
    parts = []

    for token in tokens:
        if isinstance(token, str):
            parts.append(token)
        elif isinstance(token, dict):
            text = token.get("text", "")
            style = token.get("style", {})

            if style.get("bold") and style.get("italic"):
                text = f'***{text}***'
            elif style.get("bold"):
                text = f'**{text}**'
            elif style.get("italic"):
                text = f'*{text}*'

            parts.append(text)

    return ''.join(parts)
