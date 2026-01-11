#!/usr/bin/env python3
"""
Test script for Capacities SDK Task Management functionality.

This script tests the following task operations:
1. List existing tasks (get_tasks)
2. Get pending tasks (get_pending_tasks)
3. Create a new task (create_task)
4. Complete the task (complete_task)
5. Uncomplete the task (uncomplete_task)
6. Update the task (update_task)
7. Delete the task (delete_task)

Usage:
    Set CAPACITIES_AUTH_TOKEN environment variable, then run:
    $ python capacities_sdk/test_tasks.py
"""

import os
import sys
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capacities_sdk import (
    CapacitiesClient,
    Task,
    TaskStatus,
    TaskPriority,
    CapacitiesError,
    AuthenticationError,
    NotFoundError,
)


# Test configuration - loaded from .secrets.env
from test_config import SPACE_ID, require_auth_token

TEST_TASK_TITLE = "SDK Test Task"
TEST_TASK_UPDATED_TITLE = "SDK Test Task - Updated"
TEST_TASK_DUE_DATE = "2026-01-15"
TEST_TASK_PRIORITY = TaskPriority.HIGH
TEST_TASK_NOTES = "This is a test task created by the SDK"


def get_auth_token():
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


def print_result(test_name: str, success: bool, details: str = ""):
    """Print formatted test result."""
    status = "PASS" if success else "FAIL"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"{color}[{status}]{reset} {test_name}")
    if details:
        for line in details.split("\n"):
            print(f"      {line}")


def print_task(task: Task, indent: str = "      "):
    """Print task details."""
    print(f"{indent}ID: {task.id}")
    print(f"{indent}Title: {task.title}")
    print(f"{indent}Status: {task.status.value}")
    if task.priority:
        print(f"{indent}Priority: {task.priority.value}")
    if task.due_date:
        print(f"{indent}Due Date: {task.due_date.strftime('%Y-%m-%d')}")
    if task.notes:
        print(f"{indent}Notes: {task.notes[:50]}{'...' if len(task.notes) > 50 else ''}")
    if task.completed_at:
        print(f"{indent}Completed At: {task.completed_at.isoformat()}")


def run_tests():
    """Run all task management tests."""
    print("=" * 60)
    print("Capacities SDK Task Management Tests")
    print("=" * 60)
    print()

    # Get auth token
    auth_token = get_auth_token()
    if not auth_token:
        print("\033[91mERROR: CAPACITIES_AUTH_TOKEN environment variable not set.\033[0m")
        print("\nTo set it:")
        print("  Windows: set CAPACITIES_AUTH_TOKEN=your-token")
        print("  Linux/Mac: export CAPACITIES_AUTH_TOKEN=your-token")
        print("\nGet your token from Capacities Desktop App > Settings > Capacities API")
        return False

    print(f"Space ID: {SPACE_ID}")
    print(f"Token: {auth_token[:20]}...{auth_token[-10:]}")
    print()

    # Initialize client
    try:
        client = CapacitiesClient(auth_token=auth_token)
        print_result("Initialize client", True)
    except Exception as e:
        print_result("Initialize client", False, str(e))
        return False

    created_task_id = None
    test_results = []

    # Test 1: List existing tasks
    print("\n--- Test 1: List existing tasks ---")
    try:
        tasks = client.get_tasks(SPACE_ID)
        print_result("get_tasks()", True, f"Found {len(tasks)} tasks")
        if tasks:
            print("      First few tasks:")
            for task in tasks[:3]:
                print(f"        - {task.title} ({task.status.value})")
        test_results.append(("List existing tasks", True))
    except Exception as e:
        print_result("get_tasks()", False, str(e))
        test_results.append(("List existing tasks", False))

    # Test 2: Get pending tasks
    print("\n--- Test 2: Get pending tasks ---")
    try:
        pending_tasks = client.get_pending_tasks(SPACE_ID)
        print_result("get_pending_tasks()", True, f"Found {len(pending_tasks)} pending tasks")
        test_results.append(("Get pending tasks", True))
    except Exception as e:
        print_result("get_pending_tasks()", False, str(e))
        test_results.append(("Get pending tasks", False))

    # Test 3: Create a new task
    print("\n--- Test 3: Create a new task ---")
    try:
        task = client.create_task(
            space_id=SPACE_ID,
            title=TEST_TASK_TITLE,
            due_date=TEST_TASK_DUE_DATE,
            priority=TEST_TASK_PRIORITY,
            notes=TEST_TASK_NOTES,
        )
        created_task_id = task.id
        print_result("create_task()", True)
        print_task(task)

        # Verify task properties
        assert task.title == TEST_TASK_TITLE, f"Title mismatch: {task.title}"
        assert task.priority == TEST_TASK_PRIORITY, f"Priority mismatch: {task.priority}"
        assert task.status == TaskStatus.NOT_STARTED, f"Status should be not-started: {task.status}"

        test_results.append(("Create task", True))
    except Exception as e:
        print_result("create_task()", False, str(e))
        test_results.append(("Create task", False))

    # Small delay to let API sync
    time.sleep(1)

    # Test 4: Complete the task
    print("\n--- Test 4: Complete the task ---")
    if created_task_id:
        try:
            task = client.complete_task(SPACE_ID, created_task_id)
            print_result("complete_task()", True)
            print_task(task)

            # Verify completion
            assert task.status == TaskStatus.DONE, f"Status should be done: {task.status}"
            assert task.completed_at is not None, "Should have completed_at timestamp"

            test_results.append(("Complete task", True))
        except Exception as e:
            print_result("complete_task()", False, str(e))
            test_results.append(("Complete task", False))
    else:
        print_result("complete_task()", False, "No task created to complete")
        test_results.append(("Complete task", False))

    time.sleep(1)

    # Test 5: Uncomplete the task
    print("\n--- Test 5: Uncomplete the task ---")
    if created_task_id:
        try:
            task = client.uncomplete_task(SPACE_ID, created_task_id)
            print_result("uncomplete_task()", True)
            print_task(task)

            # Verify uncomplete
            assert task.status == TaskStatus.NOT_STARTED, f"Status should be not-started: {task.status}"

            test_results.append(("Uncomplete task", True))
        except Exception as e:
            print_result("uncomplete_task()", False, str(e))
            test_results.append(("Uncomplete task", False))
    else:
        print_result("uncomplete_task()", False, "No task created to uncomplete")
        test_results.append(("Uncomplete task", False))

    time.sleep(1)

    # Test 6: Update the task
    print("\n--- Test 6: Update the task ---")
    if created_task_id:
        try:
            task = client.update_task(
                space_id=SPACE_ID,
                task_id=created_task_id,
                title=TEST_TASK_UPDATED_TITLE,
            )
            print_result("update_task()", True)
            print_task(task)

            # Verify update
            assert task.title == TEST_TASK_UPDATED_TITLE, f"Title not updated: {task.title}"

            test_results.append(("Update task", True))
        except Exception as e:
            print_result("update_task()", False, str(e))
            test_results.append(("Update task", False))
    else:
        print_result("update_task()", False, "No task created to update")
        test_results.append(("Update task", False))

    time.sleep(1)

    # Test 7: Delete the task
    print("\n--- Test 7: Delete the task ---")
    if created_task_id:
        try:
            success = client.delete_task(SPACE_ID, created_task_id)
            print_result("delete_task()", success, f"Task moved to trash: {created_task_id}")
            test_results.append(("Delete task", success))
        except Exception as e:
            print_result("delete_task()", False, str(e))
            test_results.append(("Delete task", False))
    else:
        print_result("delete_task()", False, "No task created to delete")
        test_results.append(("Delete task", False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)

    for test_name, success in test_results:
        status = "\033[92mPASS\033[0m" if success else "\033[91mFAIL\033[0m"
        print(f"  [{status}] {test_name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n\033[92mAll tests passed!\033[0m")
        return True
    else:
        print(f"\n\033[91m{total - passed} test(s) failed.\033[0m")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
