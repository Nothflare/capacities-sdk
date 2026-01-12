#!/usr/bin/env python3
"""
Test script for markdown-to-blocks functionality in Capacities SDK.

Tests:
1. Unit tests for markdown_to_blocks parser
2. Integration test: create object with rich markdown
3. Verification: fetch object and verify block types
4. Cleanup: delete test object

Usage:
    python -m capacities_sdk.test_blocks

Environment:
    CAPACITIES_AUTH_TOKEN - JWT authentication token
"""

import os
import sys
import time
from typing import Any, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capacities_sdk.blocks import (
    markdown_to_blocks,
    blocks_to_markdown,
    parse_inline_formatting,
    create_text_block,
    create_heading_block,
    create_code_block,
    create_horizontal_line_block,
    create_quote_block,
)
from capacities_sdk.client import CapacitiesClient


# Test configuration - loaded from .secrets.env
from test_config import SPACE_ID, NOTE_STRUCTURE_ID, require_auth_token


def print_header(title: str) -> None:
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(name: str, passed: bool, details: str = "") -> None:
    """Print a test result."""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status} {name}")
    if details:
        for line in details.split("\n"):
            print(f"         {line}")


def describe_block(block: Dict[str, Any], indent: int = 0) -> str:
    """Create a readable description of a block."""
    prefix = "  " * indent
    block_type = block.get("type", "Unknown")

    if block_type == "HeadingBlock":
        level = block.get("level", 1)
        text = "".join(t.get("text", "") for t in block.get("tokens", []))
        return f"{prefix}HeadingBlock (level {level}): \"{text}\""

    elif block_type == "TextBlock":
        tokens = block.get("tokens", [])
        text = "".join(t.get("text", "") for t in tokens if isinstance(t, dict))

        # Check for list type
        list_info = block.get("list", {})
        list_type = list_info.get("type", "") if list_info else ""

        # Check for quote
        quote_info = block.get("quote")

        # Check for styled tokens
        styles = []
        for token in tokens:
            if isinstance(token, dict):
                style = token.get("style", {})
                if style.get("bold"):
                    styles.append("bold")
                if style.get("italic"):
                    styles.append("italic")

        extra = []
        if list_type:
            extra.append(f"list={list_type}")
        if quote_info:
            extra.append("quote")
        if styles:
            extra.append(f"styles={set(styles)}")

        extra_str = f" ({', '.join(extra)})" if extra else ""
        return f"{prefix}TextBlock{extra_str}: \"{text[:50]}{'...' if len(text) > 50 else ''}\""

    elif block_type == "CodeBlock":
        lang = block.get("lang", "text")
        code = block.get("text", "")
        return f"{prefix}CodeBlock (lang={lang}): {len(code)} chars"

    elif block_type == "HorizontalLineBlock":
        return f"{prefix}HorizontalLineBlock"

    else:
        return f"{prefix}{block_type}: {block}"


# ==============================================================================
# UNIT TESTS
# ==============================================================================

def test_plain_text() -> bool:
    """Test plain text parsing."""
    md = "This is plain text without any formatting."
    blocks = markdown_to_blocks(md)

    if len(blocks) != 1:
        return False
    if blocks[0].get("type") != "TextBlock":
        return False

    tokens = blocks[0].get("tokens", [])
    if len(tokens) != 1:
        return False
    if tokens[0].get("text") != md:
        return False

    return True


def test_headings() -> bool:
    """Test heading levels 1-3."""
    md = """# Heading 1
## Heading 2
### Heading 3"""

    blocks = markdown_to_blocks(md)

    if len(blocks) != 3:
        print(f"    Expected 3 blocks, got {len(blocks)}")
        return False

    for i, (block, expected_level) in enumerate(zip(blocks, [1, 2, 3])):
        if block.get("type") != "HeadingBlock":
            print(f"    Block {i} is not HeadingBlock: {block.get('type')}")
            return False
        if block.get("level") != expected_level:
            print(f"    Block {i} level is {block.get('level')}, expected {expected_level}")
            return False

    return True


def test_code_block() -> bool:
    """Test fenced code blocks with language."""
    md = """```python
def hello():
    print("Hello World")
```"""

    blocks = markdown_to_blocks(md)

    if len(blocks) != 1:
        print(f"    Expected 1 block, got {len(blocks)}")
        return False

    block = blocks[0]
    if block.get("type") != "CodeBlock":
        print(f"    Block type is {block.get('type')}, expected CodeBlock")
        return False
    if block.get("lang") != "python":
        print(f"    Language is {block.get('lang')}, expected python")
        return False
    if "def hello():" not in block.get("text", ""):
        print(f"    Code content missing")
        return False

    return True


def test_bullet_list() -> bool:
    """Test unordered bullet lists."""
    md = """- Item 1
- Item 2
- Item 3"""

    blocks = markdown_to_blocks(md)

    if len(blocks) != 3:
        print(f"    Expected 3 blocks, got {len(blocks)}")
        return False

    for i, block in enumerate(blocks):
        if block.get("type") != "TextBlock":
            print(f"    Block {i} is not TextBlock")
            return False
        list_info = block.get("list", {})
        if list_info.get("type") != "unordered":
            print(f"    Block {i} list type is {list_info.get('type')}, expected unordered")
            return False

    return True


def test_numbered_list() -> bool:
    """Test ordered numbered lists."""
    md = """1. First item
2. Second item
3. Third item"""

    blocks = markdown_to_blocks(md)

    if len(blocks) != 3:
        print(f"    Expected 3 blocks, got {len(blocks)}")
        return False

    for i, block in enumerate(blocks):
        if block.get("type") != "TextBlock":
            print(f"    Block {i} is not TextBlock")
            return False
        list_info = block.get("list", {})
        if list_info.get("type") != "ordered":
            print(f"    Block {i} list type is {list_info.get('type')}, expected ordered")
            return False

    return True


def test_inline_bold() -> bool:
    """Test bold inline formatting."""
    md = "This is **bold** text."
    blocks = markdown_to_blocks(md)

    if len(blocks) != 1:
        return False

    tokens = blocks[0].get("tokens", [])

    # Should have 3 tokens: "This is ", "bold", " text."
    if len(tokens) != 3:
        print(f"    Expected 3 tokens, got {len(tokens)}: {tokens}")
        return False

    # Check the bold token
    bold_token = tokens[1]
    if bold_token.get("text") != "bold":
        print(f"    Bold token text is {bold_token.get('text')}, expected 'bold'")
        return False
    if not bold_token.get("style", {}).get("bold"):
        print(f"    Bold token is not marked as bold")
        return False

    return True


def test_inline_italic() -> bool:
    """Test italic inline formatting."""
    md = "This is *italic* text."
    blocks = markdown_to_blocks(md)

    if len(blocks) != 1:
        return False

    tokens = blocks[0].get("tokens", [])

    # Should have 3 tokens
    if len(tokens) != 3:
        print(f"    Expected 3 tokens, got {len(tokens)}")
        return False

    # Check the italic token
    italic_token = tokens[1]
    if italic_token.get("text") != "italic":
        return False
    if not italic_token.get("style", {}).get("italic"):
        return False

    return True


def test_horizontal_rule() -> bool:
    """Test horizontal rule parsing."""
    md = """Some text

---

More text"""

    blocks = markdown_to_blocks(md)

    # Should have 3 blocks: TextBlock, HorizontalLineBlock, TextBlock
    hr_blocks = [b for b in blocks if b.get("type") == "HorizontalLineBlock"]

    if len(hr_blocks) != 1:
        print(f"    Expected 1 HorizontalLineBlock, got {len(hr_blocks)}")
        return False

    return True


def test_blockquote() -> bool:
    """Test blockquote parsing."""
    md = "> This is a quote"
    blocks = markdown_to_blocks(md)

    if len(blocks) != 1:
        print(f"    Expected 1 block, got {len(blocks)}")
        return False

    block = blocks[0]
    if block.get("type") != "TextBlock":
        print(f"    Block type is {block.get('type')}, expected TextBlock")
        return False

    quote_info = block.get("quote")
    if not quote_info:
        print(f"    Block missing quote property")
        return False

    return True


def test_blocks_to_markdown() -> bool:
    """Test reverse conversion from blocks to markdown."""
    original = """# Test Heading

This is some text.

```python
print("hello")
```

---

> A quote"""

    blocks = markdown_to_blocks(original)
    reconstructed = blocks_to_markdown(blocks)

    # Re-parse to verify roundtrip
    blocks2 = markdown_to_blocks(reconstructed)

    # Same number of blocks
    if len(blocks) != len(blocks2):
        print(f"    Block count mismatch: {len(blocks)} vs {len(blocks2)}")
        return False

    # Same block types
    for i, (b1, b2) in enumerate(zip(blocks, blocks2)):
        if b1.get("type") != b2.get("type"):
            print(f"    Block {i} type mismatch: {b1.get('type')} vs {b2.get('type')}")
            return False

    return True


def run_unit_tests() -> Dict[str, bool]:
    """Run all unit tests and return results."""
    tests = {
        "Plain text": test_plain_text,
        "Headings (H1-H3)": test_headings,
        "Code block with language": test_code_block,
        "Bullet list": test_bullet_list,
        "Numbered list": test_numbered_list,
        "Bold inline formatting": test_inline_bold,
        "Italic inline formatting": test_inline_italic,
        "Horizontal rule": test_horizontal_rule,
        "Blockquote": test_blockquote,
        "Blocks to markdown roundtrip": test_blocks_to_markdown,
    }

    results = {}
    for name, test_fn in tests.items():
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"    Exception in {name}: {e}")
            results[name] = False

    return results


# ==============================================================================
# INTEGRATION TEST
# ==============================================================================

def run_integration_test(client: CapacitiesClient) -> Dict[str, Any]:
    """
    Run integration test: create object with markdown, verify, delete.

    Returns dict with test results and created object info.
    """
    results = {
        "create": False,
        "verify_blocks": False,
        "block_types_found": [],
        "delete": False,
        "object_id": None,
        "error": None,
    }

    # Rich markdown content to test
    test_markdown = """# Test Heading

This is **bold** and *italic* text.

## Code Example

```python
def hello():
    print("Hello World")
```

- Item 1
- Item 2

---

> A quote"""

    try:
        # Step 1: Create object with markdown
        print("\n  Creating test object with rich markdown...")
        obj = client.create_object(
            space_id=SPACE_ID,
            structure_id=NOTE_STRUCTURE_ID,
            title="[TEST] Markdown Blocks Test",
            content=test_markdown,
        )

        if not obj:
            results["error"] = "create_object returned None"
            return results

        results["object_id"] = obj.id
        results["create"] = True
        print(f"    Created object: {obj.id}")

        # Small delay to ensure sync
        time.sleep(1)

        # Step 2: Fetch and verify blocks
        print("\n  Fetching object to verify blocks...")
        fetched = client.get_object(obj.id)

        if not fetched:
            results["error"] = "get_object returned None"
            return results

        # Analyze blocks
        block_types = set()
        has_heading_1 = False
        has_heading_2 = False
        has_code_block = False
        has_python_lang = False
        has_list = False
        has_horizontal = False
        has_quote = False
        has_bold = False
        has_italic = False

        print("\n  Blocks found in object:")

        for prop_id, block_list in fetched.blocks.items():
            print(f"\n    Property: {prop_id[:8]}...")
            for block in block_list:
                # Get raw block data
                raw_blocks = fetched.raw_data.get("data", {}).get("blocks", {}).get(prop_id, [])
                for raw_block in raw_blocks:
                    block_type = raw_block.get("type", "")
                    block_types.add(block_type)
                    print(f"      {describe_block(raw_block)}")

                    if block_type == "HeadingBlock":
                        level = raw_block.get("level", 0)
                        if level == 1:
                            has_heading_1 = True
                        elif level == 2:
                            has_heading_2 = True

                    elif block_type == "CodeBlock":
                        has_code_block = True
                        if raw_block.get("lang") == "python":
                            has_python_lang = True

                    elif block_type == "TextBlock":
                        if raw_block.get("list"):
                            has_list = True
                        if raw_block.get("quote"):
                            has_quote = True

                        # Check for styled tokens
                        for token in raw_block.get("tokens", []):
                            if isinstance(token, dict):
                                style = token.get("style", {})
                                if style.get("bold"):
                                    has_bold = True
                                if style.get("italic"):
                                    has_italic = True

                    elif block_type == "HorizontalLineBlock":
                        has_horizontal = True

        results["block_types_found"] = list(block_types)

        # Verification summary
        print("\n  Block verification:")
        verifications = [
            ("HeadingBlock (level 1)", has_heading_1),
            ("HeadingBlock (level 2)", has_heading_2),
            ("CodeBlock with python", has_code_block and has_python_lang),
            ("TextBlock with list", has_list),
            ("HorizontalLineBlock", has_horizontal),
            ("TextBlock with quote", has_quote),
            ("Bold styled token", has_bold),
            ("Italic styled token", has_italic),
        ]

        all_verified = True
        for name, found in verifications:
            status = "[OK]" if found else "[MISSING]"
            print(f"    {status} {name}")
            if not found:
                all_verified = False

        results["verify_blocks"] = all_verified

        # Step 3: Delete test object
        print("\n  Deleting test object...")
        deleted = client.delete_object(SPACE_ID, obj.id)
        results["delete"] = deleted
        print(f"    Deleted: {deleted}")

    except Exception as e:
        results["error"] = str(e)
        import traceback
        traceback.print_exc()

        # Try to cleanup if object was created
        if results["object_id"]:
            try:
                print(f"\n  Attempting cleanup of {results['object_id']}...")
                client.delete_object(SPACE_ID, results["object_id"])
            except Exception:
                pass

    return results


# ==============================================================================
# MAIN
# ==============================================================================

def get_auth_token() -> str:
    """Get auth token from environment or .env file."""
    token = os.environ.get("CAPACITIES_AUTH_TOKEN")

    if not token:
        # Try to load from .env file if python-dotenv is available
        try:
            from dotenv import load_dotenv
            env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path)
                token = os.environ.get("CAPACITIES_AUTH_TOKEN")
        except ImportError:
            pass

    return token


def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("  CAPACITIES SDK - MARKDOWN TO BLOCKS TEST")
    print("#" * 60)

    # -------------------------------------------------------------------------
    # Unit Tests
    # -------------------------------------------------------------------------
    print_header("UNIT TESTS: markdown_to_blocks Parser")

    unit_results = run_unit_tests()

    for name, passed in unit_results.items():
        print_result(name, passed)

    unit_passed = sum(1 for v in unit_results.values() if v)
    unit_total = len(unit_results)
    print(f"\n  Unit test summary: {unit_passed}/{unit_total} passed")

    # -------------------------------------------------------------------------
    # Integration Tests
    # -------------------------------------------------------------------------
    print_header("INTEGRATION TEST: Create Object with Markdown")

    # Get auth token
    auth_token = get_auth_token()
    if not auth_token:
        print("  [SKIP] CAPACITIES_AUTH_TOKEN not set")
        print("         Set this environment variable to run integration tests.")
        print("         Windows: set CAPACITIES_AUTH_TOKEN=your-token")
        print("         Linux/Mac: export CAPACITIES_AUTH_TOKEN=your-token")
        print("         Or create a .env file with CAPACITIES_AUTH_TOKEN=your-token")
        integration_passed = False
    else:
        print(f"  Auth token found: {auth_token[:20]}...")
        print(f"  Space ID: {SPACE_ID}")
        print(f"  Structure ID: {NOTE_STRUCTURE_ID}")

        client = CapacitiesClient(auth_token=auth_token)
        integration_results = run_integration_test(client)

        print_header("INTEGRATION TEST RESULTS")
        print_result("Object created", integration_results["create"])
        print_result("Blocks verified", integration_results["verify_blocks"],
                    f"Types found: {integration_results['block_types_found']}")
        print_result("Object deleted", integration_results["delete"])

        if integration_results["error"]:
            print(f"\n  [ERROR] {integration_results['error']}")

        integration_passed = (
            integration_results["create"] and
            integration_results["verify_blocks"] and
            integration_results["delete"]
        )

    # -------------------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------------------
    print_header("FINAL SUMMARY")

    all_unit_passed = all(unit_results.values())

    print(f"  Unit tests:        {'PASS' if all_unit_passed else 'FAIL'} ({unit_passed}/{unit_total})")
    if auth_token:
        print(f"  Integration tests: {'PASS' if integration_passed else 'FAIL'}")
    else:
        print(f"  Integration tests: SKIPPED (no auth token)")

    overall = all_unit_passed and (integration_passed if auth_token else True)
    print(f"\n  Overall: {'PASS' if overall else 'FAIL'}")

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
