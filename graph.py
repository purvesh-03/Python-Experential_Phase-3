"""Adjacency-list social graph and traversal algorithms."""
from collections import deque


class GraphError(ValueError):
    """Raised for invalid graph operations."""


class SocialGraph:
    """Undirected graph stored as ``graph[user] = set_of_friends``."""

    def __init__(self):
        self.adj = {}

    # ---- construction -------------------------------------------------
    @classmethod
    def from_data(cls, users, friendships):
        g = cls()
        for u in users:
            g.add_user(u)
        for a, b in friendships:
            g.add_friendship(a, b)
        return g

    def add_user(self, name):
        if name in self.adj:
            raise GraphError(f"User '{name}' already exists.")
        self.adj[name] = set()

    def remove_user(self, name):
        self._require(name)
        for friend in self.adj[name]:
            self.adj[friend].discard(name)
        del self.adj[name]

    def add_friendship(self, a, b):
        self._require(a)
        self._require(b)
        if a == b:
            raise GraphError("A user cannot be friends with themselves.")
        if b in self.adj[a]:
            raise GraphError(f"{a} and {b} are already friends.")
        self.adj[a].add(b)
        self.adj[b].add(a)

    def remove_friendship(self, a, b):
        self._require(a)
        self._require(b)
        if b not in self.adj[a]:
            raise GraphError(f"{a} and {b} are not friends.")
        self.adj[a].discard(b)
        self.adj[b].discard(a)

    # ---- queries ------------------------------------------------------
    def _require(self, name):
        if name not in self.adj:
            raise GraphError(f"User '{name}' does not exist.")

    def users(self):
        return sorted(self.adj, key=str.lower)

    def friends(self, name):
        self._require(name)
        return sorted(self.adj[name], key=str.lower)

    def edges(self):
        seen = set()
        for a, friends in self.adj.items():
            for b in friends:
                seen.add(tuple(sorted((a, b), key=str.lower)))
        return sorted(seen, key=lambda e: (e[0].lower(), e[1].lower()))

    # ---- algorithms ---------------------------------------------------
    def bfs(self, start):
        """Return the BFS visit order of the component containing start."""
        self._require(start)
        visited = {start}
        order = []
        queue = deque([start])
        while queue:
            node = queue.popleft()
            order.append(node)
            for nxt in sorted(self.adj[node], key=str.lower):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return order

    def shortest_path(self, source, target):
        """Return list of users from source to target, or None if unreachable."""
        self._require(source)
        self._require(target)
        if source == target:
            return [source]
        parent = {source: None}
        queue = deque([source])
        while queue:
            node = queue.popleft()
            for nxt in sorted(self.adj[node], key=str.lower):
                if nxt in parent:
                    continue
                parent[nxt] = node
                if nxt == target:
                    path = [nxt]
                    while parent[path[-1]] is not None:
                        path.append(parent[path[-1]])
                    return path[::-1]
                queue.append(nxt)
        return None
