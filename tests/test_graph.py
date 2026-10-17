"""
test_graph.py - Unit tests for SocialGraph data structure & core operations
Phase 3: Social Network Friend Recommendation System
"""

import unittest
from graph import SocialGraph


class TestSocialGraph(unittest.TestCase):

    def setUp(self):
        self.g = SocialGraph()
        self.g.add_user("u1", "Alice", "Engineer")
        self.g.add_user("u2", "Bob", "Designer")
        self.g.add_user("u3", "Charlie", "Data Analyst")

    def test_add_user_success(self):
        ok, res = self.g.add_user("u4", "Diana", "Product Manager")
        self.assertTrue(ok)
        self.assertEqual(res["name"], "Diana")
        self.assertIn("u4", self.g.users)
        self.assertIn("u4", self.g.adj)
        self.assertEqual(len(self.g.adj["u4"]), 0)

    def test_add_duplicate_user_id(self):
        ok, msg = self.g.add_user("u1", "Duplicate Alice", "Dev")
        self.assertFalse(ok)
        self.assertIn("already exists", msg)

    def test_add_duplicate_user_name_case_insensitive(self):
        ok, msg = self.g.add_user("u4", "alice", "Dev")
        self.assertFalse(ok)
        self.assertIn("already exists", msg)

    def test_add_empty_user(self):
        ok, msg = self.g.add_user("", "Valid Name")
        self.assertFalse(ok)
        ok2, msg2 = self.g.add_user("u4", "")
        self.assertFalse(ok2)

    def test_remove_user_and_cascade(self):
        self.g.add_friendship("u1", "u2")
        self.g.add_friendship("u1", "u3")
        self.assertTrue(self.g.are_friends("u1", "u2"))

        ok, msg = self.g.remove_user("u1")
        self.assertTrue(ok)
        self.assertNotIn("u1", self.g.users)
        self.assertNotIn("u1", self.g.adj)
        # Verify u1 is removed from Bob and Charlie's friend sets
        self.assertNotIn("u1", self.g.adj["u2"])
        self.assertNotIn("u1", self.g.adj["u3"])

    def test_remove_nonexistent_user(self):
        ok, msg = self.g.remove_user("nonexistent_id")
        self.assertFalse(ok)

    def test_add_friendship_undirected_symmetry(self):
        ok, msg = self.g.add_friendship("u1", "u2")
        self.assertTrue(ok)
        self.assertTrue(self.g.are_friends("u1", "u2"))
        self.assertTrue(self.g.are_friends("u2", "u1"))
        self.assertIn("u2", self.g.adj["u1"])
        self.assertIn("u1", self.g.adj["u2"])

    def test_self_friendship_prevention(self):
        ok, msg = self.g.add_friendship("u1", "u1")
        self.assertFalse(ok)
        self.assertIn("themselves", msg)

    def test_duplicate_friendship_prevention(self):
        self.g.add_friendship("u1", "u2")
        ok, msg = self.g.add_friendship("u1", "u2")
        self.assertFalse(ok)
        self.assertIn("already friends", msg)
        # Try reverse order
        ok2, msg2 = self.g.add_friendship("u2", "u1")
        self.assertFalse(ok2)
        self.assertIn("already friends", msg2)

    def test_friendship_with_nonexistent_user(self):
        ok, msg = self.g.add_friendship("u1", "u999")
        self.assertFalse(ok)
        self.assertIn("do not exist", msg)

    def test_remove_friendship(self):
        self.g.add_friendship("u1", "u2")
        self.assertTrue(self.g.are_friends("u1", "u2"))
        ok, msg = self.g.remove_friendship("u1", "u2")
        self.assertTrue(ok)
        self.assertFalse(self.g.are_friends("u1", "u2"))
        self.assertFalse(self.g.are_friends("u2", "u1"))

    def test_remove_nonexistent_friendship(self):
        ok, msg = self.g.remove_friendship("u1", "u2")
        self.assertFalse(ok)
        self.assertIn("not friends", msg)

    def test_network_statistics_calculation(self):
        # Initial: 3 users, 0 friendships, 3 isolated
        stats = self.g.get_statistics()
        self.assertEqual(stats["total_users"], 3)
        self.assertEqual(stats["total_friendships"], 0)
        self.assertEqual(stats["isolated_users_count"], 3)

        # Add friendship: u1 - u2
        self.g.add_friendship("u1", "u2")
        stats = self.g.get_statistics()
        self.assertEqual(stats["total_friendships"], 1)
        self.assertEqual(stats["isolated_users_count"], 1)  # u3 is isolated
        self.assertEqual(stats["most_connected_count"], 1)


if __name__ == "__main__":
    unittest.main()
