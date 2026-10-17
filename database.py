"""
database.py - Persistent Database Interface (SQLite & Managed PostgreSQL)
Phase 3: Social Network Friend Recommendation System

Supports:
1. Local Development: Built-in Python sqlite3 module (zero external setup).
2. Production Deployment: Managed PostgreSQL (e.g., Neon, Supabase, Vercel Postgres)
   via DATABASE_URL or POSTGRES_URL environment variables with pg8000.
3. Fallback Resilience: Automatically uses /tmp/social_network.db in serverless read-only
   environments if DATABASE_URL is not yet configured, preventing boot crashes.
4. Parameterized SQL queries throughout to eliminate SQL injection vulnerabilities.
"""

import os
import sqlite3
import ssl
import sys
import tempfile
import urllib.parse

# Default seed members for initial network population
DEFAULT_SEED_USERS = [
    ("u1", "Alex Rivera", "Tech Lead & Distributed Systems Engineer"),
    ("u2", "Bella Chen", "UI/UX Designer & Product Researcher"),
    ("u3", "Carlos Mendez", "Data Scientist & Python Algorithm Specialist"),
    ("u4", "Diana Prince", "Product Strategist & Cloud Architect"),
    ("u5", "Ethan Hunt", "Cybersecurity Analyst & Network Engineer"),
    ("u6", "Fiona Gallagher", "Full-Stack Web Engineer & Open Source Contributor"),
    ("u7", "George Clark", "DevOps Engineer & Infrastructure Specialist"),
    ("u8", "Hannah Abbott", "Community Coordinator & Technical Writer")
]

DEFAULT_SEED_FRIENDSHIPS = [
    ("u1", "u2"),  # Alex - Bella
    ("u1", "u3"),  # Alex - Carlos
    ("u1", "u4"),  # Alex - Diana
    ("u2", "u3"),  # Bella - Carlos
    ("u2", "u5"),  # Bella - Ethan
    ("u3", "u4"),  # Carlos - Diana
    ("u3", "u6"),  # Carlos - Fiona
    ("u4", "u7"),  # Diana - George
    ("u5", "u6"),  # Ethan - Fiona
    ("u6", "u7"),  # Fiona - George
    ("u6", "u8"),  # Fiona - Hannah
    ("u7", "u8")   # George - Hannah
]


class Database:
    """
    Unified database interface for the Social Network application.
    Abstracts differences between SQLite and PostgreSQL.
    """

    def __init__(self, db_url=None):
        self.db_url = db_url or os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        self.is_postgres = False

        if self.db_url and (
            self.db_url.startswith("postgres://") or self.db_url.startswith("postgresql://")
        ):
            self.is_postgres = True
        else:
            self.is_postgres = False
            # Determine appropriate SQLite path
            configured_path = os.environ.get("DATABASE_PATH")
            if configured_path:
                self.sqlite_path = configured_path
            elif os.environ.get("VERCEL"):
                # Vercel serverless environment has read-only root; /tmp is writable
                self.sqlite_path = os.path.join(tempfile.gettempdir(), "social_network.db")
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                self.sqlite_path = os.path.join(base_dir, "social_network.db")

    def get_connection(self):
        """Returns an active database connection."""
        if self.is_postgres:
            try:
                import pg8000.dbapi
            except ImportError:
                raise ImportError(
                    "pg8000 is required for PostgreSQL connections. Install it via 'pip install pg8000'."
                )

            parsed = urllib.parse.urlparse(self.db_url)
            query_params = urllib.parse.parse_qs(parsed.query)

            # SSL context for cloud hosted PostgreSQL (Neon, Supabase, etc.)
            ssl_context = None
            if query_params.get("sslmode", [""])[0] in ["require", "prefer", "verify-ca", "verify-full"] or True:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            conn = pg8000.dbapi.connect(
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path.lstrip("/"),
                ssl_context=ssl_context
            )
            return conn
        else:
            conn = sqlite3.connect(self.sqlite_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            # Enable foreign keys for SQLite
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn

    def _format_query(self, query):
        """Converts standard '?' placeholders to '%s' if using PostgreSQL."""
        if self.is_postgres:
            return query.replace("?", "%s")
        return query

    def execute_query(self, query, params=(), commit=False):
        """
        Executes a parameterized query and handles committing and closing connection.
        Returns: cursor or rows affected.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            formatted_query = self._format_query(query)
            cursor.execute(formatted_query, params)
            if commit:
                conn.commit()
            return cursor
        except Exception:
            if commit:
                conn.rollback()
            raise
        finally:
            conn.close()

    def fetch_all(self, query, params=()):
        """Executes a parameterized SELECT query and returns all rows as list of dicts."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            formatted_query = self._format_query(query)
            cursor.execute(formatted_query, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            result = []
            for row in rows:
                if isinstance(row, sqlite3.Row):
                    result.append(dict(row))
                else:
                    # pg8000 tuple
                    result.append(dict(zip(columns, row)))
            return result
        finally:
            conn.close()

    def fetch_one(self, query, params=()):
        """Executes a parameterized SELECT query and returns the first row as a dict, or None."""
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    # -------------------------------------------------------------
    # Schema Initialization & Migrations
    # -------------------------------------------------------------

    def init_db(self):
        """Creates the users and friendships tables if they do not already exist."""
        users_table_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(128) UNIQUE NOT NULL,
            bio TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        friendships_table_sql = """
        CREATE TABLE IF NOT EXISTS friendships (
            user1_id VARCHAR(64) NOT NULL,
            user2_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user1_id, user2_id),
            FOREIGN KEY (user1_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (user2_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(users_table_sql)
            cursor.execute(friendships_table_sql)
            conn.commit()
        finally:
            conn.close()

    def seed_initial_data_if_empty(self):
        """
        Populates default college social network data if the users table is empty.
        Ensures the application is immediately testable upon startup.
        """
        row = self.fetch_one("SELECT COUNT(*) AS count FROM users;")
        count = row["count"] if row else 0

        if count == 0:
            conn = self.get_connection()
            try:
                cursor = conn.cursor()
                # Insert users
                for uid, name, bio in DEFAULT_SEED_USERS:
                    user_q = self._format_query(
                        "INSERT INTO users (id, name, bio) VALUES (?, ?, ?);"
                    )
                    cursor.execute(user_q, (uid, name, bio))

                # Insert friendships (normalized u1 < u2)
                for u1, u2 in DEFAULT_SEED_FRIENDSHIPS:
                    pair_a = min(u1, u2)
                    pair_b = max(u1, u2)
                    friend_q = self._format_query(
                        "INSERT INTO friendships (user1_id, user2_id) VALUES (?, ?);"
                    )
                    cursor.execute(friend_q, (pair_a, pair_b))

                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # -------------------------------------------------------------
    # Data Access Methods
    # -------------------------------------------------------------

    def get_all_users(self):
        """Returns all users ordered alphabetically by name."""
        return self.fetch_all("SELECT id, name, bio, created_at FROM users ORDER BY name ASC;")

    def get_user_by_id(self, user_id):
        """Returns a user by their unique ID."""
        return self.fetch_one("SELECT id, name, bio, created_at FROM users WHERE id = ?;", (user_id,))

    def get_user_by_name(self, name):
        """Returns a user by their exact or case-insensitive name."""
        return self.fetch_one("SELECT id, name, bio, created_at FROM users WHERE LOWER(name) = LOWER(?);", (name.strip(),))

    def create_user(self, user_id, name, bio="Member"):
        """Inserts a new user into the database."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            q = self._format_query("INSERT INTO users (id, name, bio) VALUES (?, ?, ?);")
            cursor.execute(q, (user_id, name, bio))
            conn.commit()
            return True, self.get_user_by_id(user_id)
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def update_user(self, user_id, name, bio):
        """Updates a user's name and bio."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            q = self._format_query("UPDATE users SET name = ?, bio = ? WHERE id = ?;")
            cursor.execute(q, (name, bio, user_id))
            conn.commit()
            return True, self.get_user_by_id(user_id)
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def delete_user(self, user_id):
        """Deletes a user and their associated friendships."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Clean up friendships explicitly (also handled by ON DELETE CASCADE)
            del_f = self._format_query("DELETE FROM friendships WHERE user1_id = ? OR user2_id = ?;")
            cursor.execute(del_f, (user_id, user_id))

            del_u = self._format_query("DELETE FROM users WHERE id = ?;")
            cursor.execute(del_u, (user_id,))
            conn.commit()
            return True, "User deleted successfully."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def get_all_friendships(self):
        """Returns all friendship pairs from the database."""
        return self.fetch_all("SELECT user1_id, user2_id, created_at FROM friendships;")

    def create_friendship(self, u1, u2):
        """Inserts a friendship between two users."""
        pair_a = min(u1, u2)
        pair_b = max(u1, u2)
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            q = self._format_query(
                "INSERT INTO friendships (user1_id, user2_id) VALUES (?, ?);"
            )
            cursor.execute(q, (pair_a, pair_b))
            conn.commit()
            return True, "Friendship persisted."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def delete_friendship(self, u1, u2):
        """Removes a friendship between two users."""
        pair_a = min(u1, u2)
        pair_b = max(u1, u2)
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            q = self._format_query(
                "DELETE FROM friendships WHERE user1_id = ? AND user2_id = ?;"
            )
            cursor.execute(q, (pair_a, pair_b))
            conn.commit()
            return True, "Friendship removed."
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def load_graph_from_db(self, graph):
        """
        Synchronizes an in-memory SocialGraph instance with the persisted database records.
        """
        graph.clear()

        # Load all users
        users = self.get_all_users()
        for u in users:
            graph.add_user(
                user_id=u["id"],
                name=u["name"],
                bio=u.get("bio", "Member"),
                created_at=str(u.get("created_at", ""))
            )

        # Load all friendships
        friendships = self.get_all_friendships()
        for f in friendships:
            u1 = f["user1_id"]
            u2 = f["user2_id"]
            if u1 in graph.users and u2 in graph.users:
                graph.adj[u1].add(u2)
                graph.adj[u2].add(u1)


# Global Database singleton
db = Database()
