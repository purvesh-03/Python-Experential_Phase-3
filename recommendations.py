"""Mutual friends, recommendations and network statistics."""


def mutual_friends(graph, a, b):
    graph._require(a)
    graph._require(b)
    if a == b:
        return []
    return sorted(graph.adj[a] & graph.adj[b], key=str.lower)


def recommend(graph, user, limit=None):
    """Friends-of-friends ranked by mutual count (desc), then name (asc)."""
    graph._require(user)
    direct = graph.adj[user]
    counts = {}
    for friend in direct:
        for candidate in graph.adj[friend]:
            if candidate == user or candidate in direct:
                continue
            counts.setdefault(candidate, set()).add(friend)
    results = []
    for cand, via in counts.items():
        via_sorted = sorted(via, key=str.lower)
        n = len(via_sorted)
        noun = "friend" if n == 1 else "friends"
        results.append({
            "name": cand,
            "mutual_count": n,
            "mutual_friends": via_sorted,
            "explanation": f"{n} mutual {noun}: {', '.join(via_sorted)}.",
        })
    results.sort(key=lambda r: (-r["mutual_count"], r["name"].lower()))
    return results[:limit] if limit else results


def network_statistics(graph):
    users = graph.users()
    total_users = len(users)
    total_friendships = len(graph.edges())
    avg = (2 * total_friendships / total_users) if total_users else 0.0
    top = None
    if users:
        top_name = max(users, key=lambda u: (len(graph.adj[u]), -users.index(u)))
        top = {"name": top_name, "friends": len(graph.adj[top_name])}
    isolated = [u for u in users if not graph.adj[u]]
    with_recs = sum(1 for u in users if recommend(graph, u))
    total_recs = sum(len(recommend(graph, u)) for u in users)
    return {
        "total_users": total_users,
        "total_friendships": total_friendships,
        "average_friends": round(avg, 2),
        "most_connected": top,
        "isolated_count": len(isolated),
        "isolated_users": isolated,
        "users_with_recommendations": with_recs,
        "total_recommendations": total_recs,
    }
