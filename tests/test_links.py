#!/usr/bin/env python3
"""Test script for Capacities SDK link management functionality.

Tests the following link operations:
- get_links: Get all outgoing links (LinkTokens and EntityBlocks) from an object
- get_linked_objects: Get full Object instances for all linked objects
- get_backlinks: Find all objects linking TO an object
- add_link: Create a link from one object to another (inline or block)

Key insight: Links in Capacities are stored as LinkTokens INSIDE content blocks,
NOT in the entity-level linkNodes array. The implementation creates LinkTokens
with `entity.id` pointing to the target.

Usage:
    Option 1: Set CAPACITIES_AUTH_TOKEN environment variable
        export CAPACITIES_AUTH_TOKEN=your-token
        python test_links.py

    Option 2: Pass token as command-line argument
        python test_links.py --token your-token

    Option 3: Create a .env file in the project root with:
        CAPACITIES_AUTH_TOKEN=your-token
"""

import argparse
import os
import sys
import time

# Add parent directory to path for importing the SDK
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capacities_sdk import CapacitiesClient


# Test configuration - loaded from .secrets.env
from test_config import SPACE_ID, NOTE_STRUCTURE_ID, require_auth_token


def print_separator(title: str):
    """Print a visual separator with title."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_link_info(links: list):
    """Pretty print link information."""
    if not links:
        print("  (no links found)")
        return
    for i, link in enumerate(links, 1):
        print(f"  Link {i}:")
        print(f"    - Target ID: {link.get('target_id', 'N/A')}")
        print(f"    - Target Structure: {link.get('target_structure_id', 'N/A')}")
        print(f"    - Display Text: {link.get('display_text', 'N/A')}")
        print(f"    - Link Type: {link.get('type', 'N/A')}")


def print_object_summary(obj, indent="  "):
    """Print a summary of an object."""
    print(f"{indent}ID: {obj.id}")
    print(f"{indent}Title: {obj.title}")
    print(f"{indent}Structure: {obj.structure_id}")


def main():
    """Run link management tests."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Test Capacities SDK link management functionality"
    )
    parser.add_argument(
        "--token", "-t",
        help="Capacities API auth token (alternative to CAPACITIES_AUTH_TOKEN env var)"
    )
    args = parser.parse_args()

    print("\n" + "#" * 70)
    print("#  CAPACITIES SDK - LINK MANAGEMENT TEST")
    print("#  Testing LinkTokens stored in content blocks")
    print("#" * 70)

    # Get auth token
    auth_token = get_auth_token(args.token)
    if not auth_token:
        print("\nERROR: No authentication token provided")
        print("\nTo provide a token, use one of these methods:")
        print("  1. Command line: python test_links.py --token YOUR_TOKEN")
        print("  2. Environment:  export CAPACITIES_AUTH_TOKEN=YOUR_TOKEN")
        print("  3. .env file:    Add CAPACITIES_AUTH_TOKEN=YOUR_TOKEN to .env")
        print("\nGet your token from Capacities Desktop App > Settings > Capacities API")
        sys.exit(1)

    # Initialize client
    print("\nInitializing CapacitiesClient...")
    client = CapacitiesClient(auth_token)
    print("  Client initialized successfully")

    # Track created objects for cleanup
    source_id = None
    target_id = None
    test_results = {}

    try:
        # =====================================================================
        # STEP 1: Find existing objects with links
        # =====================================================================
        print_separator("STEP 1: Search for Existing Objects with Links")

        print("\nSearching space for objects with existing links...")
        all_objects = client.get_all_objects(SPACE_ID)
        print(f"  Found {len(all_objects)} total objects in space")

        objects_with_links = []
        for obj in all_objects:
            links = obj.get_links()
            if links:
                objects_with_links.append((obj, links))

        print(f"  Objects with links: {len(objects_with_links)}")

        if objects_with_links:
            print("\n  Sample objects with links:")
            for obj, links in objects_with_links[:3]:  # Show first 3
                print(f"\n    '{obj.title}' ({obj.id[:8]}...):")
                print(f"      Links: {len(links)}")
                for link in links[:2]:  # Show first 2 links
                    print(f"        -> {link.target_id[:8]}... ({link.display_text or 'no text'})")
            test_results["find_existing_links"] = "PASS"
        else:
            print("  No existing objects with links found (this is OK)")
            test_results["find_existing_links"] = "SKIP (no existing links)"

        # =====================================================================
        # STEP 2: Test get_links() on object with links
        # =====================================================================
        print_separator("STEP 2: Test get_links() Method")

        if objects_with_links:
            test_obj, test_links = objects_with_links[0]
            print(f"\nTesting get_links() on: '{test_obj.title}'")

            # Use client method
            links_via_client = client.get_links(test_obj.id)
            print(f"\n  client.get_links() returned {len(links_via_client)} link(s):")
            print_link_info(links_via_client)

            # Compare with object method
            links_via_object = test_obj.get_links()
            print(f"\n  obj.get_links() returned {len(links_via_object)} link(s)")

            if len(links_via_client) == len(links_via_object):
                print("  VERIFIED: Both methods return same count")
                test_results["get_links"] = "PASS"
            else:
                print("  WARNING: Method counts differ")
                test_results["get_links"] = "WARN"
        else:
            print("\nSkipping - no objects with links to test")
            test_results["get_links"] = "SKIP"

        # =====================================================================
        # STEP 3: Test get_linked_objects()
        # =====================================================================
        print_separator("STEP 3: Test get_linked_objects() Method")

        if objects_with_links:
            test_obj, _ = objects_with_links[0]
            print(f"\nGetting linked objects for: '{test_obj.title}'")

            linked_objects = client.get_linked_objects(test_obj.id)
            print(f"\n  Retrieved {len(linked_objects)} linked object(s):")

            for linked_obj in linked_objects[:5]:  # Show first 5
                print(f"\n    Linked to:")
                print_object_summary(linked_obj, indent="      ")

            if linked_objects:
                test_results["get_linked_objects"] = "PASS"
            else:
                test_results["get_linked_objects"] = "WARN (no objects retrieved)"
        else:
            print("\nSkipping - no objects with links to test")
            test_results["get_linked_objects"] = "SKIP"

        # =====================================================================
        # STEP 4: Create test objects
        # =====================================================================
        print_separator("STEP 4: Create Test Objects")

        print("\nCreating 'Link Source' object...")
        source = client.create_object(
            space_id=SPACE_ID,
            structure_id=NOTE_STRUCTURE_ID,
            title="SDK Test - Link Source",
            content="This object will contain outgoing links to the target."
        )
        source_id = source.id
        print("  SUCCESS: Source object created")
        print_object_summary(source)

        print("\nCreating 'Link Target' object...")
        target = client.create_object(
            space_id=SPACE_ID,
            structure_id=NOTE_STRUCTURE_ID,
            title="SDK Test - Link Target",
            content="This object will be linked TO from the source."
        )
        target_id = target.id
        print("  SUCCESS: Target object created")
        print_object_summary(target)

        test_results["create_objects"] = "PASS"

        # Small delay for API sync
        time.sleep(1.0)

        # =====================================================================
        # STEP 5: Test add_link() - Inline link
        # =====================================================================
        print_separator("STEP 5: Test add_link() - Inline LinkToken")

        print(f"\nCreating inline link from Source -> Target...")
        print(f"  Source: {source_id}")
        print(f"  Target: {target_id}")

        updated_source = client.add_link(
            space_id=SPACE_ID,
            source_object_id=source_id,
            target_object_id=target_id,
            display_text="Link to Target",
            as_block=False
        )

        print("\n  SUCCESS: Inline link created!")

        # Verify the link was created
        time.sleep(0.5)
        links_after = client.get_links(source_id)
        print(f"\n  Verifying... Source now has {len(links_after)} link(s):")
        print_link_info(links_after)

        # Check if target is in links
        link_targets = [l.get("target_id") for l in links_after]
        if target_id in link_targets:
            print("\n  VERIFIED: Link correctly points to Target object")
            test_results["add_link_inline"] = "PASS"
        else:
            print("\n  WARNING: Target not found in links!")
            test_results["add_link_inline"] = "FAIL"

        # =====================================================================
        # STEP 6: Test get_backlinks()
        # =====================================================================
        print_separator("STEP 6: Test get_backlinks()")

        print(f"\nFinding backlinks to Target ({target_id[:8]}...)...")
        print("  (This searches all objects in the space)")

        backlinks = client.get_backlinks(
            space_id=SPACE_ID,
            object_id=target_id
        )

        print(f"\n  Found {len(backlinks)} object(s) linking to Target:")
        for obj in backlinks:
            print(f"\n    Backlink from:")
            print_object_summary(obj, indent="      ")

        # Verify source is in backlinks
        backlink_ids = [obj.id for obj in backlinks]
        if source_id in backlink_ids:
            print("\n  VERIFIED: Source object found in backlinks")
            test_results["get_backlinks"] = "PASS"
        else:
            print("\n  WARNING: Source object not found in backlinks")
            test_results["get_backlinks"] = "FAIL"

        # =====================================================================
        # STEP 7: Test add_link() with as_block=True
        # =====================================================================
        print_separator("STEP 7: Test add_link() with as_block=True (EntityBlock)")

        print(f"\nCreating EntityBlock link from Source -> Target...")

        # Create another target for this test
        print("\nCreating second target object for block link test...")
        target2 = client.create_object(
            space_id=SPACE_ID,
            structure_id=NOTE_STRUCTURE_ID,
            title="SDK Test - Block Link Target",
            content="This object will be embedded as an EntityBlock."
        )
        target2_id = target2.id
        print(f"  Created: {target2.title} ({target2_id[:8]}...)")

        time.sleep(0.5)

        updated_source = client.add_link(
            space_id=SPACE_ID,
            source_object_id=source_id,
            target_object_id=target2_id,
            as_block=True
        )

        print("\n  SUCCESS: EntityBlock link created!")

        # Verify the link was created
        time.sleep(0.5)
        links_after_block = client.get_links(source_id)
        print(f"\n  Source now has {len(links_after_block)} link(s):")
        print_link_info(links_after_block)

        # Check if target2 is in links
        link_targets = [l.get("target_id") for l in links_after_block]
        if target2_id in link_targets:
            print("\n  VERIFIED: EntityBlock link created successfully")
            test_results["add_link_block"] = "PASS"
        else:
            print("\n  WARNING: EntityBlock target not found in links!")
            test_results["add_link_block"] = "FAIL"

        # =====================================================================
        # STEP 8: Cleanup - Delete test objects
        # =====================================================================
        print_separator("STEP 8: Cleanup - Delete Test Objects")

        print("\nDeleting Source object...")
        if client.delete_object(SPACE_ID, source_id):
            print("  SUCCESS: Source object deleted")
            source_id = None  # Mark as deleted
        else:
            print("  WARNING: Failed to delete Source object")

        print("\nDeleting Target object...")
        if client.delete_object(SPACE_ID, target_id):
            print("  SUCCESS: Target object deleted")
            target_id = None  # Mark as deleted
        else:
            print("  WARNING: Failed to delete Target object")

        print("\nDeleting second Target object...")
        if client.delete_object(SPACE_ID, target2_id):
            print("  SUCCESS: Second Target object deleted")
        else:
            print("  WARNING: Failed to delete second Target object")

        test_results["cleanup"] = "PASS"

        # =====================================================================
        # Summary
        # =====================================================================
        print_separator("TEST SUMMARY")

        print("\n  Test Results:")
        print("  " + "-" * 50)

        all_passed = True
        for test_name, result in test_results.items():
            status_icon = "[OK]" if result == "PASS" else "[--]" if "SKIP" in result else "[!!]"
            print(f"  {status_icon} {test_name}: {result}")
            if result == "FAIL":
                all_passed = False

        print("\n  " + "-" * 50)
        print("""
  Link Implementation Details:
    - Links are stored as LinkTokens INSIDE content blocks
    - NOT in the entity-level linkNodes array (usually empty)
    - LinkTokens have: entity.id -> target object UUID
    - EntityBlocks embed objects as block-level references
    - get_links() extracts both LinkTokens and EntityBlocks
    - get_backlinks() searches all objects for references
""")

    except Exception as e:
        print(f"\n\nERROR: Test failed with exception:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

        # Cleanup on error
        print("\n\nAttempting cleanup after error...")
        if source_id:
            try:
                client.delete_object(SPACE_ID, source_id)
                print(f"  Deleted Source: {source_id}")
            except Exception:
                print(f"  Failed to delete Source: {source_id}")
        if target_id:
            try:
                client.delete_object(SPACE_ID, target_id)
                print(f"  Deleted Target: {target_id}")
            except Exception:
                print(f"  Failed to delete Target: {target_id}")

        sys.exit(1)

    if all_passed:
        print("\n" + "#" * 70)
        print("#  ALL TESTS PASSED SUCCESSFULLY")
        print("#" * 70 + "\n")
    else:
        print("\n" + "#" * 70)
        print("#  SOME TESTS FAILED - SEE RESULTS ABOVE")
        print("#" * 70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
