#!/usr/bin/env python3
"""Test script for Knowledge Graph integration."""

import asyncio
import sys
sys.path.insert(0, "/Users/vladcortex/co-founder/backend")

from app.memory.knowledge_graph import get_knowledge_graph


SAMPLE_PYTHON = '''
"""Sample module for testing."""

from typing import List
import os

class UserService:
    """Handles user operations."""

    def __init__(self, db):
        self.db = db

    def get_user(self, user_id: str):
        """Get a user by ID."""
        return self.db.query(user_id)

    def create_user(self, name: str, email: str):
        """Create a new user."""
        return self.db.insert({"name": name, "email": email})


class AdminService(UserService):
    """Admin-specific operations."""

    def delete_user(self, user_id: str):
        """Delete a user."""
        return self.db.delete(user_id)


def main():
    """Entry point."""
    service = UserService(None)
    print(service.get_user("123"))
'''


async def test_knowledge_graph():
    kg = get_knowledge_graph()

    print("1. Initializing schema...")
    try:
        await kg.initialize_schema()
        print("   ✓ Schema initialized")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return

    print("\n2. Indexing sample Python file...")
    try:
        result = await kg.index_file(
            file_path="src/services/user.py",
            content=SAMPLE_PYTHON,
            project_id="test-project",
        )
        print(f"   ✓ Indexed {result['entities_indexed']} entities, {result['relations_indexed']} relations")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return

    print("\n3. Searching for 'Service' entities...")
    try:
        results = await kg.search_entities(
            project_id="test-project",
            query="Service",
            entity_type="class",
        )
        for r in results:
            print(f"   - {r['type']}: {r['name']} ({r['file_path']})")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    print("\n4. Getting impact analysis for user.py...")
    try:
        impact = await kg.get_impact_analysis(
            project_id="test-project",
            file_path="src/services/user.py",
        )
        print(f"   Entities in file: {len(impact['entities'])}")
        print(f"   Affected files: {impact['affected_count']}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    print("\n✓ Knowledge Graph test complete!")
    await kg.close()


if __name__ == "__main__":
    asyncio.run(test_knowledge_graph())
