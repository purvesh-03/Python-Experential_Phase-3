"""
graph.py - Social Network Graph Representation & Core Graph Operations
Phase 3: Social Network Friend Recommendation System

Implements an undirected graph using an Adjacency List data structure:
- Users: Dictionary mapping user_id to user metadata dict
- Adjacency List: Dictionary mapping user_id to a set of friend user_ids: graph[user_id] = set_of_friends
- Real Graph Algorithms: BFS Traversal, Shortest Path, Network Statistics
"""

from collections import deque
import time


class SocialGraph:
    """
    Graph data structure representing users as vertices and friendships as undirected edges.
    Uses Python dictionaries and sets for O(1) average lookup, addition, and removal.
    """

    def __init__(self):
        # Maps user_id -> dict of user attributes: {"id": str, "name": str, "bio": str, "created_at": str}
        self.users = {}
        # Maps user_id -> set of friend user_ids: { "u1": {"u2", "u3"}, ... }
        self.adj = {}

    def clear(self):
        """Clears all users and friendships from the in-memory graph."""
        self.users.clear()
        self.adj.clear()

    # -------------------------------------------------------------
    # User Management
    # -------------------------------------------------------------

    def add_user(self, user_id, name, bio="Member", created_at=None):
        """
        Adds a new user vertex to the graph.
        Returns: (success: bool, message/user: dict or str)
        """
        user_id = str(user_id).strip()
        name = str(name).strip()
        bio = str(bio).strip() if bio else "Member"

        if not user_id:
            return False, "User ID cannot be empty."
        if not name:
            return False, "User name cannot be empty."

        if user_id in self.users:
            return False, f"User with ID '{user_id}' already exists."

        # Case-insensitive duplicate name check
        for existing in self.users.values():
            if existing["name"].lower() == name.lower():
                return False, f"A user named '{name}' already exists."

        user_data = {
            "id": user_id,
            "name": name,
            "bio": bio,
            "created_at": created_at or time.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.users[user_id] = user_data
        self.adj[user_id] = set()
        return True, user_data

    def get_user(self, user_id):
        """Returns the user dictionary or None if not found."""
        return self.users.get(str(user_id).strip())

    def get_user_by_name(self, name):
        """Finds a user by name (case-insensitive)."""
        name_clean = str(name).strip().lower()
        for user in self.users.values():
            if user["name"].lower() == name_clean:
                return user
        return None

    def search_users(self, query):
        """Searches for users whose name or bio contains the query substring."""
        query = str(query).strip().lower()
        if not query:
            return list(self.users.values())
        return [
            u for u in self.users.values()
            if query in u["name"].lower() or query in u["bio"].lower()
        ]

    def remove_user(self, user_id):
        """
        Removes a user and cascades by deleting all incident friendship edges.
        Returns: (success: bool, message: str)
        """
        user_id = str(user_id).strip()
        if user_id not in self.users:
            return False, f"User '{user_id}' not found."

        # Remove this user from all connected friends' adjacency sets
        for friend_id in list(self.adj.get(user_id, [])):
            if friend_id in self.adj:
                self.adj[friend_id].discard(user_id)

        user_name = self.users[user_id]["name"]
        del self.adj[user_id]
        del self.users[user_id]
        return True, f"User '{user_name}' and all associated connections removed."

    def get_all_users(self):
        """Returns a list of all user dictionaries sorted alphabetically by name."""
        return sorted(self.users.values(), key=lambda u: u["name"].lower())

    # -------------------------------------------------------------
    # Friendship Management (Undirected Edges)
    # -------------------------------------------------------------

    def add_friendship(self, u1, u2):
        """
        Creates an undirected friendship edge between u1 and u2:
        self.adj[u1].add(u2) and self.adj[u2].add(u1)
        Returns: (success: bool, message: str)
        """
        u1 = str(u1).strip()
        u2 = str(u2).strip()

        if not u1 or not u2:
            return False, "User IDs cannot be empty."

        if u1 not in self.users or u2 not in self.users:
            return False, "One or both users do not exist in the network."

        if u1 == u2:
            return False, "A user cannot be friends with themselves."

        if u2 in self.adj[u1]:
            return False, f"'{self.users[u1]['name']}' and '{self.users[u2]['name']}' are already friends."

        self.adj[u1].add(u2)
        self.adj[u2].add(u1)
        return True, f"Friendship established between {self.users[u1]['name']} and {self.users[u2]['name']}."

    def remove_friendship(self, u1, u2):
        """
        Removes the undirected friendship edge between u1 and u2.
        Returns: (success: bool, message: str)
        """
        u1 = str(u1).strip()
        u2 = str(u2).strip()

        if u1 not in self.users or u2 not in self.users:
            return False, "One or both users do not exist."

        if u2 not in self.adj.get(u1, set()):
            return False, f"'{self.users[u1]['name']}' and '{self.users[u2]['name']}' are not friends."

        self.adj[u1].discard(u2)
        self.adj[u2].discard(u1)
        return True, f"Friendship removed between {self.users[u1]['name']} and {self.users[u2]['name']}."

    def are_friends(self, u1, u2):
        """Returns True if u1 and u2 have a direct friendship edge."""
        u1 = str(u1).strip()
        u2 = str(u2).strip()
        return u1 in self.adj and u2 in self.adj.get(u1, set())

    def get_friends(self, user_id):
        """Returns a list of user dictionaries who are direct friends of user_id."""
        user_id = str(user_id).strip()
        if user_id not in self.adj:
            return []
        friend_ids = sorted(self.adj[user_id], key=lambda fid: self.users[fid]["name"].lower())
        return [self.users[fid] for fid in friend_ids if fid in self.users]

    def get_all_friendships(self):
        """
        Returns a list of unique undirected friendships as tuples:
        [(user1_dict, user2_dict), ...] where user1_id < user2_id to prevent duplicates.
        """
        edges = []
        seen = set()
        for u1, friends in self.adj.items():
            for u2 in friends:
                edge_key = tuple(sorted([u1, u2]))
                if edge_key not in seen:
                    seen.add(edge_key)
                    if u1 in self.users and u2 in self.users:
                        # Normalize order by alphabetical name
                        user_a = self.users[edge_key[0]]
                        user_b = self.users[edge_key[1]]
                        edges.append((user_a, user_b))
        edges.sort(key=lambda pair: (pair[0]["name"].lower(), pair[1]["name"].lower()))
        return edges

    # -------------------------------------------------------------
    # Breadth-First Search (BFS) Traversal
    # -------------------------------------------------------------

    def bfs_traversal(self, start_user_id):
        """
        Performs Breadth-First Search traversal starting from start_user_id using collections.deque.
        Explores the connected component level-by-level.
        Returns:
            dict containing:
            - "success": bool
            - "start_user": dict or None
            - "order": list of dicts with user info and level/distance
            - "visited_count": int
            - "message": str
        """
        start_user_id = str(start_user_id).strip()
        if start_user_id not in self.users:
            return {
                "success": False,
                "start_user": None,
                "order": [],
                "visited_count": 0,
                "message": f"Starting user '{start_user_id}' does not exist."
            }

        visited = {start_user_id}
        queue = deque([(start_user_id, 0)])  # (user_id, level)
        traversal_order = []

        while queue:
            current_id, level = queue.popleft()
            user_info = dict(self.users[current_id])
            user_info["level"] = level
            traversal_order.append(user_info)

            # Sort neighbor IDs alphabetically by name for deterministic traversal
            neighbors = sorted(
                self.adj.get(current_id, set()),
                key=lambda uid: self.users[uid]["name"].lower() if uid in self.users else uid
            )

            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, level + 1))

        return {
            "success": True,
            "start_user": self.users[start_user_id],
            "order": traversal_order,
            "visited_count": len(traversal_order),
            "message": f"BFS completed with {len(traversal_order)} user(s) in connected component."
        }

    # -------------------------------------------------------------
    # Shortest Connection Path (BFS)
    # -------------------------------------------------------------

    def shortest_path(self, start_user_id, dest_user_id):
        """
        Finds the shortest friendship connection path between start_user_id and dest_user_id using BFS.
        BFS guarantees the shortest path in unweighted graphs.
        Returns:
            dict containing:
            - "success": bool
            - "found": bool
            - "start_user": dict or None
            - "dest_user": dict or None
            - "path": list of user dictionaries from start to dest
            - "links": int (number of friendship links, len(path) - 1)
            - "message": str
        """
        start_user_id = str(start_user_id).strip()
        dest_user_id = str(dest_user_id).strip()

        if start_user_id not in self.users or dest_user_id not in self.users:
            return {
                "success": False,
                "found": False,
                "start_user": self.users.get(start_user_id),
                "dest_user": self.users.get(dest_user_id),
                "path": [],
                "links": 0,
                "message": "One or both users do not exist in the network."
            }

        start_user = self.users[start_user_id]
        dest_user = self.users[dest_user_id]

        if start_user_id == dest_user_id:
            return {
                "success": True,
                "found": True,
                "start_user": start_user,
                "dest_user": dest_user,
                "path": [start_user],
                "links": 0,
                "message": "Starting user and destination user are the same person (distance 0)."
            }

        # BFS queue stores (current_node, path_so_far)
        queue = deque([(start_user_id, [start_user_id])])
        visited = {start_user_id}

        while queue:
            current_id, path_ids = queue.popleft()

            if current_id == dest_user_id:
                full_path = [self.users[uid] for uid in path_ids if uid in self.users]
                return {
                    "success": True,
                    "found": True,
                    "start_user": start_user,
                    "dest_user": dest_user,
                    "path": full_path,
                    "links": len(full_path) - 1,
                    "message": f"Shortest path found with {len(full_path) - 1} friendship link(s)."
                }

            neighbors = sorted(
                self.adj.get(current_id, set()),
                key=lambda uid: self.users[uid]["name"].lower() if uid in self.users else uid
            )

            for neighbor_id in neighbors:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path_ids + [neighbor_id]))

        return {
            "success": True,
            "found": False,
            "start_user": start_user,
            "dest_user": dest_user,
            "path": [],
            "links": 0,
            "message": f"No connection path exists between '{start_user['name']}' and '{dest_user['name']}'. They belong to separate network components."
        }

    # -------------------------------------------------------------
    # Dynamically Calculated Network Statistics
    # -------------------------------------------------------------

    def get_statistics(self):
        """
        Dynamically calculates comprehensive network metrics from the current stored graph.
        All values are calculated in Python without fabricated or static numbers.
        """
        total_users = len(self.users)
        if total_users == 0:
            return {
                "total_users": 0,
                "total_friendships": 0,
                "avg_friends_per_user": 0.0,
                "most_connected_user": None,
                "most_connected_count": 0,
                "isolated_users_count": 0,
                "isolated_users": [],
                "network_density": 0.0,
                "degree_distribution": {}
            }

        # Each edge is stored twice in undirected adjacency list, so divide by 2
        total_friendships = sum(len(friends) for friends in self.adj.values()) // 2
        avg_friends = round((2 * total_friendships) / total_users, 2)

        # Isolated users (degree = 0)
        isolated_users = [
            self.users[uid] for uid, friends in self.adj.items()
            if len(friends) == 0 and uid in self.users
        ]
        isolated_users.sort(key=lambda u: u["name"].lower())

        # Most connected user (highest degree)
        most_connected_user = None
        max_friends = -1
        degree_distribution = {}

        for uid, user in self.users.items():
            deg = len(self.adj.get(uid, set()))
            degree_distribution[user["name"]] = deg
            if deg > max_friends:
                max_friends = deg
                most_connected_user = user

        # Network density: 2 * E / (V * (V - 1)) for undirected graph
        if total_users > 1:
            max_possible_edges = (total_users * (total_users - 1)) / 2
            density = round(total_friendships / max_possible_edges, 4)
        else:
            density = 0.0

        return {
            "total_users": total_users,
            "total_friendships": total_friendships,
            "avg_friends_per_user": avg_friends,
            "most_connected_user": most_connected_user,
            "most_connected_count": max(0, max_friends),
            "isolated_users_count": len(isolated_users),
            "isolated_users": isolated_users,
            "network_density": density,
            "degree_distribution": degree_distribution
        }
