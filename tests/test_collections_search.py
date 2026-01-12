#!/usr/bin/env python3
"""
Test script for Capacities SDK collections and full-text search functionality.

Tests:
1. Collection operations (add/remove objects, get collection objects)
2. Full-text search across content

Usage:
    python test_collections_search.py [--token YOUR_TOKEN]

    Or set CAPACITIES_AUTH_TOKEN environment variable

Requires:
    - CAPACITIES_AUTH_TOKEN environment variable or --token argument
"""

import argparse
import os
import sys
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capacities_sdk import CapacitiesClient
from capacities_sdk.exceptions import CapacitiesError, NotFoundError


# Test configuration - loaded from .secrets.env
from test_config import SPACE_ID, NOTE_STRUCTURE_ID, require_auth_token


def get_auth_token() -> str:
    """Get auth token from environment or command line."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Test Capacities SDK collections and search")
    parser.add_argument("--token", "-t", help="Capacities auth token")
    args, _ = parser.parse_known_args()

    # Check command line first
    if args.token:
        return args.token

    # Then environment variable
    token = os.environ.get("CAPACITIES_AUTH_TOKEN")
    if token:
        return token

    # Try to load from .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("CAPACITIES_AUTH_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"\'')

    return None


def print_header(title: str):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_success(message: str):
    """Print a success message."""
    print(f"  [OK] {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"  [ERROR] {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"  [INFO] {message}")


def test_collections(client: CapacitiesClient) -> dict:
    """Test collection operations."""
    print_header("TESTING COLLECTION OPERATIONS")

    results = {
        "test_object_id": None,
        "collection_id": None,
        "add_success": False,
        "get_object_collections_success": False,
        "get_collection_objects_success": False,
        "remove_success": False,
        "verify_removal_success": False,
        "cleanup_success": False,
        "errors": []
    }

    # Step 1: Find existing collections by scanning object databases
    # Note: We use Portal API only since Public API requires different auth
    print("\n1. Finding collections by scanning existing objects...")
    try:
        # Get all objects in space
        all_objects_brief = client.list_space_objects(SPACE_ID)
        print_info(f"Space has {len(all_objects_brief)} total objects")

        # Find collection/database IDs by checking which objects have databases
        database_ids = []

        # Sample objects to find database/collection IDs
        sample_size = min(50, len(all_objects_brief))
        sample_ids = [obj["id"] for obj in all_objects_brief[:sample_size]]
        sample_objects = client.get_objects_by_ids(sample_ids)

        for obj in sample_objects:
            for db in obj.raw_data.get("databases", []):
                db_id = db.get("id")
                if db_id and db_id not in database_ids:
                    database_ids.append(db_id)

        if database_ids:
            results["collection_id"] = database_ids[0]
            print_success(f"Found {len(database_ids)} collection(s)")
            print_info(f"Using collection ID: {results['collection_id']}")
        else:
            print_info("No existing collections found in the space")
            print_info("Collection tests will be limited without an existing collection")

    except Exception as e:
        error_msg = f"Failed to get space info: {e}"
        print_error(error_msg)
        results["errors"].append(error_msg)

    # Step 2: Create a test object
    print("\n2. Creating test object for collection testing...")
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_note = client.create_object(
            space_id=SPACE_ID,
            structure_id=NOTE_STRUCTURE_ID,
            title=f"SDK Collection Test Note {timestamp}",
            content=f"""This is a test note created by the SDK collection test script.

## Test Information
- Created at: {timestamp}
- Purpose: Testing collection operations
- Keywords: SDK, collection, test, automation

This content includes various keywords to test full-text search functionality.
"""
        )
        results["test_object_id"] = test_note.id
        print_success(f"Created test object: {test_note.id}")
        print_info(f"Title: {test_note.title}")

        # Small delay to ensure sync
        time.sleep(1)

    except Exception as e:
        error_msg = f"Failed to create test object: {e}"
        print_error(error_msg)
        results["errors"].append(error_msg)
        return results

    # Step 3: Test add_to_collection (if we have a collection)
    if results["collection_id"] and results["test_object_id"]:
        print(f"\n3. Adding object to collection...")
        try:
            updated_obj = client.add_to_collection(
                space_id=SPACE_ID,
                object_id=results["test_object_id"],
                collection_id=results["collection_id"]
            )
            results["add_success"] = True
            print_success(f"Added object to collection")

            # Show updated databases
            db_count = len(updated_obj.raw_data.get("databases", []))
            print_info(f"Object now in {db_count} database(s)")

            time.sleep(1)

        except Exception as e:
            error_msg = f"Failed to add to collection: {e}"
            print_error(error_msg)
            results["errors"].append(error_msg)
    else:
        print("\n3. Skipping add_to_collection - no collection available")

    # Step 4: Test get_object_collections
    if results["test_object_id"]:
        print("\n4. Getting object's collections...")
        try:
            collections = client.get_object_collections(results["test_object_id"])
            results["get_object_collections_success"] = True
            print_success(f"Retrieved object collections")
            print_info(f"Object is in {len(collections)} collection(s)")
            for col_id in collections:
                print_info(f"  - Collection: {col_id}")

            # Verify our collection is in the list
            if results["collection_id"] and results["add_success"]:
                if results["collection_id"] in collections:
                    print_success("Verified: test collection is in the list")
                else:
                    print_error("Test collection NOT found in object's collections")

        except Exception as e:
            error_msg = f"Failed to get object collections: {e}"
            print_error(error_msg)
            results["errors"].append(error_msg)

    # Step 5: Test get_collection_objects
    if results["collection_id"]:
        print(f"\n5. Getting all objects in collection...")
        try:
            collection_objects = client.get_collection_objects(
                space_id=SPACE_ID,
                collection_id=results["collection_id"]
            )
            results["get_collection_objects_success"] = True
            print_success(f"Retrieved collection objects")
            print_info(f"Collection has {len(collection_objects)} object(s)")

            # List first few objects
            for i, obj in enumerate(collection_objects[:5]):
                print_info(f"  {i+1}. {obj.title}")
            if len(collection_objects) > 5:
                print_info(f"  ... and {len(collection_objects) - 5} more")

            # Verify our test object is in the collection
            if results["add_success"]:
                test_obj_in_collection = any(
                    obj.id == results["test_object_id"]
                    for obj in collection_objects
                )
                if test_obj_in_collection:
                    print_success("Verified: test object is in collection")
                else:
                    print_error("Test object NOT found in collection objects")

        except Exception as e:
            error_msg = f"Failed to get collection objects: {e}"
            print_error(error_msg)
            results["errors"].append(error_msg)
    else:
        print("\n5. Skipping get_collection_objects - no collection available")

    # Step 6: Test remove_from_collection
    if results["collection_id"] and results["test_object_id"] and results["add_success"]:
        print(f"\n6. Removing object from collection...")
        try:
            updated_obj = client.remove_from_collection(
                space_id=SPACE_ID,
                object_id=results["test_object_id"],
                collection_id=results["collection_id"]
            )
            results["remove_success"] = True
            print_success("Removed object from collection")

            db_count = len(updated_obj.raw_data.get("databases", []))
            print_info(f"Object now in {db_count} database(s)")

            time.sleep(1)

        except Exception as e:
            error_msg = f"Failed to remove from collection: {e}"
            print_error(error_msg)
            results["errors"].append(error_msg)
    else:
        print("\n6. Skipping remove_from_collection - prerequisites not met")

    # Step 7: Verify removal
    if results["remove_success"]:
        print("\n7. Verifying object was removed from collection...")
        try:
            collections = client.get_object_collections(results["test_object_id"])

            if results["collection_id"] not in collections:
                results["verify_removal_success"] = True
                print_success("Verified: object no longer in test collection")
            else:
                print_error("Object still in collection after removal")

            print_info(f"Object is now in {len(collections)} collection(s)")

        except Exception as e:
            error_msg = f"Failed to verify removal: {e}"
            print_error(error_msg)
            results["errors"].append(error_msg)
    else:
        print("\n7. Skipping removal verification - remove was not performed")

    # Step 8: Clean up - delete test object
    if results["test_object_id"]:
        print("\n8. Cleaning up - deleting test object...")
        try:
            success = client.delete_object(SPACE_ID, results["test_object_id"])
            if success:
                results["cleanup_success"] = True
                print_success("Deleted test object (moved to trash)")
            else:
                print_error("Delete returned False")
        except Exception as e:
            error_msg = f"Failed to delete test object: {e}"
            print_error(error_msg)
            results["errors"].append(error_msg)

    return results


def test_fulltext_search(client: CapacitiesClient) -> dict:
    """Test full-text search functionality."""
    print_header("TESTING FULL-TEXT SEARCH")

    results = {
        "search_queries": [],
        "errors": []
    }

    # Test queries - common terms likely to exist
    test_queries = [
        "test",
        "SDK",
        "note",
        "the",  # Very common word
    ]

    for query in test_queries:
        print(f"\n[Search] Query: '{query}'")
        query_result = {
            "query": query,
            "success": False,
            "result_count": 0,
            "sample_results": [],
            "content_matches": 0
        }

        try:
            search_results = client.search_content(
                space_id=SPACE_ID,
                query=query,
                limit=10
            )

            query_result["success"] = True
            query_result["result_count"] = len(search_results)

            if search_results:
                print_success(f"Found {len(search_results)} result(s)")

                # Check for content matches (not just title matches)
                for obj in search_results[:5]:
                    title_match = query.lower() in obj.title.lower()
                    content = obj.get_content_text()
                    content_match = content and query.lower() in content.lower()
                    desc_match = obj.description and query.lower() in obj.description.lower()

                    match_type = []
                    if title_match:
                        match_type.append("title")
                    if content_match:
                        match_type.append("content")
                        query_result["content_matches"] += 1
                    if desc_match:
                        match_type.append("description")

                    query_result["sample_results"].append({
                        "id": obj.id,
                        "title": obj.title[:50] + "..." if len(obj.title) > 50 else obj.title,
                        "match_in": match_type
                    })

                    match_str = ", ".join(match_type) if match_type else "unknown"
                    print_info(f"  - {obj.title[:40]}... (match in: {match_str})")

                if len(search_results) > 5:
                    print_info(f"  ... and {len(search_results) - 5} more results")

                if query_result["content_matches"] > 0:
                    print_success(f"Found {query_result['content_matches']} content match(es)")
            else:
                print_info("No results found")

        except Exception as e:
            error_msg = f"Search failed for '{query}': {e}"
            print_error(error_msg)
            query_result["error"] = str(e)
            results["errors"].append(error_msg)

        results["search_queries"].append(query_result)
        time.sleep(0.5)  # Small delay between queries

    # Additional test: create an object with specific content and search for it
    print("\n[Search] Testing content-specific search...")
    unique_term = f"uniqueterm{int(time.time())}"

    try:
        # Create object with unique content
        test_obj = client.create_object(
            space_id=SPACE_ID,
            structure_id=NOTE_STRUCTURE_ID,
            title="Fulltext Search Test Note",
            content=f"""This note contains a unique searchable term: {unique_term}

The purpose is to verify that full-text search can find content within the body of notes,
not just in titles.
"""
        )
        print_info(f"Created test object with unique term: {unique_term}")

        # Wait for indexing
        time.sleep(2)

        # Search for the unique term
        search_results = client.search_content(
            space_id=SPACE_ID,
            query=unique_term,
            limit=10
        )

        found_test_obj = any(obj.id == test_obj.id for obj in search_results)

        if found_test_obj:
            print_success(f"Successfully found object by content search!")
            results["content_search_verified"] = True
        else:
            print_info(f"Object not found in search results (may need longer indexing time)")
            print_info(f"Search returned {len(search_results)} results")
            results["content_search_verified"] = False

        # Clean up
        client.delete_object(SPACE_ID, test_obj.id)
        print_info("Cleaned up test object")

    except Exception as e:
        error_msg = f"Content-specific search test failed: {e}"
        print_error(error_msg)
        results["errors"].append(error_msg)
        results["content_search_verified"] = False

    return results


def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print(" CAPACITIES SDK - Collections & Full-Text Search Tests")
    print("#" * 60)

    # Check for auth token
    auth_token = get_auth_token()
    if not auth_token:
        print("\nERROR: No authentication token found")
        print("Please either:")
        print("  1. Set CAPACITIES_AUTH_TOKEN environment variable")
        print("  2. Pass --token YOUR_TOKEN as argument")
        print("  3. Create a .env file with CAPACITIES_AUTH_TOKEN=your-token")
        sys.exit(1)

    print_info(f"Space ID: {SPACE_ID}")
    print_info(f"Note Structure ID: {NOTE_STRUCTURE_ID}")

    # Initialize client
    try:
        client = CapacitiesClient(auth_token=auth_token)
        print_success("Client initialized")
    except Exception as e:
        print(f"\nERROR: Failed to initialize client: {e}")
        sys.exit(1)

    # Verify connection by listing objects (uses Portal API, not Public API)
    print("\nVerifying connection...")
    try:
        # Use list_space_objects instead of get_spaces to verify connection
        # get_spaces() uses the Public API which requires different auth
        objects = client.list_space_objects(SPACE_ID)
        print_success(f"Connected! Found {len(objects)} objects in space")
    except Exception as e:
        print(f"\nERROR: Failed to verify connection: {e}")
        sys.exit(1)

    # Run tests
    all_results = {}

    # Test collections
    collection_results = test_collections(client)
    all_results["collections"] = collection_results

    # Test full-text search
    search_results = test_fulltext_search(client)
    all_results["fulltext_search"] = search_results

    # Print summary
    print_header("TEST SUMMARY")

    print("\nCollection Tests:")
    if collection_results["collection_id"]:
        print_info(f"Collection ID used: {collection_results['collection_id']}")
    else:
        print_info("No collection available for testing")

    print(f"  - Add to collection: {'PASS' if collection_results['add_success'] else 'SKIP/FAIL'}")
    print(f"  - Get object collections: {'PASS' if collection_results['get_object_collections_success'] else 'FAIL'}")
    print(f"  - Get collection objects: {'PASS' if collection_results['get_collection_objects_success'] else 'SKIP/FAIL'}")
    print(f"  - Remove from collection: {'PASS' if collection_results['remove_success'] else 'SKIP/FAIL'}")
    print(f"  - Verify removal: {'PASS' if collection_results['verify_removal_success'] else 'SKIP/FAIL'}")
    print(f"  - Cleanup: {'PASS' if collection_results['cleanup_success'] else 'FAIL'}")

    print("\nFull-Text Search Tests:")
    for query_result in search_results.get("search_queries", []):
        status = "PASS" if query_result["success"] else "FAIL"
        content_info = f" ({query_result['content_matches']} content matches)" if query_result.get("content_matches", 0) > 0 else ""
        print(f"  - Search '{query_result['query']}': {status} - {query_result['result_count']} results{content_info}")

    content_verified = search_results.get("content_search_verified", False)
    print(f"  - Content-specific search verified: {'YES' if content_verified else 'NO'}")

    # Count errors
    total_errors = len(collection_results.get("errors", [])) + len(search_results.get("errors", []))
    if total_errors > 0:
        print(f"\nTotal Errors: {total_errors}")
        for error in collection_results.get("errors", []):
            print(f"  - {error}")
        for error in search_results.get("errors", []):
            print(f"  - {error}")
    else:
        print("\nAll tests completed without errors!")

    print("\n" + "=" * 60)
    print(" Tests Complete")
    print("=" * 60 + "\n")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
