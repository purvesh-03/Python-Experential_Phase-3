"""
recommendations.py - Mutual Friends & Friend Recommendation Engine
Phase 3: Social Network Friend Recommendation System

Implements:
1. Mutual Friends calculation using Python set intersection:
   mutual = graph.adj[u1] & graph.adj[u2]
2. Friend Recommendation Engine:
   - Scans Friends-of-Friends (FoF)
   - Excludes the target user
   - Excludes current direct friends
   - Calculates mutual friends count
   - Ranks candidates by:
     1. Mutual friend count (descending)
     2. Candidate name (ascending, for deterministic tie-breaking)
   - Generates natural, informative explanation strings for each recommendation
"""

import time


def get_mutual_friends(graph, u1, u2):
    """
    Calculates mutual friends between two users using set intersection:
    mutual_ids = graph.adj[u1] & graph.adj[u2]

    Returns:
        dict containing:
        - "success": bool
        - "user1": dict or None
        - "user2": dict or None
        - "mutual_friends": list of user dictionaries
        - "count": int
        - "message": str
    """
    u1 = str(u1).strip()
    u2 = str(u2).strip()

    if u1 not in graph.users or u2 not in graph.users:
        return {
            "success": False,
            "user1": graph.users.get(u1),
            "user2": graph.users.get(u2),
            "mutual_friends": [],
            "count": 0,
            "message": "One or both users do not exist in the network."
        }

    user1 = graph.users[u1]
    user2 = graph.users[u2]

    if u1 == u2:
        return {
            "success": True,
            "user1": user1,
            "user2": user2,
            "mutual_friends": [],
            "count": 0,
            "message": "Cannot calculate mutual friends for the same user."
        }

    # Set intersection of adjacency sets
    friends_u1 = graph.adj.get(u1, set())
    friends_u2 = graph.adj.get(u2, set())
    mutual_ids = friends_u1.intersection(friends_u2)

    mutual_list = [graph.users[mid] for mid in mutual_ids if mid in graph.users]
    mutual_list.sort(key=lambda u: u["name"].lower())

    if mutual_list:
        names = ", ".join(u["name"] for u in mutual_list)
        msg = f"Found {len(mutual_list)} mutual friend(s): {names}."
    else:
        msg = f"No mutual friends between '{user1['name']}' and '{user2['name']}'."

    return {
        "success": True,
        "user1": user1,
        "user2": user2,
        "mutual_friends": mutual_list,
        "count": len(mutual_list),
        "message": msg
    }


def recommend_friends(graph, user_id, limit=None):
    """
    Recommends new friends for user_id based on Friends-of-Friends (FoF) analysis.

    Algorithm Rules:
    1. Exclude the selected user.
    2. Exclude existing direct friends.
    3. Find candidates through friends-of-friends.
    4. Calculate the number of mutual friends for every candidate.
    5. Rank candidates by mutual-friend count in descending order.
    6. Use candidate name alphabetical order as secondary tie-breaker.
    7. Generate a clear explanation for each candidate.

    Returns:
        dict containing:
        - "success": bool
        - "user": dict or None
        - "recommendations": list of recommendation dicts
        - "total_candidates": int
        - "execution_time_ms": float
        - "message": str
    """
    start_time = time.perf_counter()
    user_id = str(user_id).strip()

    if user_id not in graph.users:
        return {
            "success": False,
            "user": None,
            "recommendations": [],
            "total_candidates": 0,
            "execution_time_ms": 0.0,
            "message": f"User '{user_id}' does not exist in the network."
        }

    target_user = graph.users[user_id]
    direct_friends = graph.adj.get(user_id, set())

    # If user has no friends, FoF cannot recommend any candidates
    if not direct_friends:
        elapsed = round((time.perf_counter() - start_time) * 1000, 3)
        return {
            "success": True,
            "user": target_user,
            "recommendations": [],
            "total_candidates": 0,
            "execution_time_ms": elapsed,
            "message": f"'{target_user['name']}' has no connections yet. Add friends first to receive recommendations."
        }

    # Discover candidate friends-of-friends
    candidate_scores = {}

    for friend_id in direct_friends:
        for fof_id in graph.adj.get(friend_id, set()):
            # Rule 1: Exclude self
            # Rule 2: Exclude existing direct friends
            if fof_id != user_id and fof_id not in direct_friends and fof_id in graph.users:
                if fof_id not in candidate_scores:
                    # Calculate mutual friends via set intersection
                    mutual_ids = direct_friends.intersection(graph.adj.get(fof_id, set()))
                    mutual_users = [graph.users[mid] for mid in mutual_ids if mid in graph.users]
                    mutual_users.sort(key=lambda u: u["name"].lower())

                    candidate_scores[fof_id] = {
                        "user": graph.users[fof_id],
                        "mutual_count": len(mutual_users),
                        "mutual_friends": mutual_users
                    }

    # Format recommendations with explanations
    rec_list = []
    for cand_id, data in candidate_scores.items():
        cand_user = data["user"]
        m_count = data["mutual_count"]
        m_friends = data["mutual_friends"]

        # Human-readable explanation
        if m_count == 1:
            explanation = f"Connected through mutual friend {m_friends[0]['name']}"
        elif m_count == 2:
            explanation = f"Connected through {m_friends[0]['name']} and {m_friends[1]['name']}"
        else:
            names = ", ".join(u["name"] for u in m_friends[:2])
            remaining = m_count - 2
            explanation = f"Connected through {names}, and {remaining} other mutual connection(s)"

        rec_list.append({
            "user": cand_user,
            "mutual_count": m_count,
            "mutual_friends": m_friends,
            "explanation": explanation
        })

    # Rule 5 & 6: Rank candidates by mutual_count (descending), then candidate name (ascending)
    rec_list.sort(key=lambda item: (-item["mutual_count"], item["user"]["name"].lower()))

    if limit and limit > 0:
        rec_list = rec_list[:limit]

    elapsed = round((time.perf_counter() - start_time) * 1000, 3)

    return {
        "success": True,
        "user": target_user,
        "recommendations": rec_list,
        "total_candidates": len(rec_list),
        "execution_time_ms": elapsed,
        "message": f"Generated {len(rec_list)} recommendation(s) in {elapsed} ms."
    }
