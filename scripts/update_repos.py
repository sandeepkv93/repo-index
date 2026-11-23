#!/usr/bin/env python3
"""
Repository Index Updater

Fetches owned public non-fork GitHub repositories for sandeepkv93 via gh CLI,
updates index.db, prunes deleted/private/forked repositories, and refreshes
language statistics using only the Python standard library.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

USERNAME = "sandeepkv93"


class RepoIndexUpdater:
    def __init__(self, db_path: str = "index.db"):
        """Initialize the repository index updater."""
        self.db_path = db_path
        self.conn = None
        self.setup_database()

    def setup_database(self):
        """Create or migrate database tables if needed."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                url TEXT NOT NULL,
                homepage_url TEXT,
                primary_language TEXT,
                star_count INTEGER DEFAULT 0,
                fork_count INTEGER DEFAULT 0,
                is_fork BOOLEAN DEFAULT FALSE,
                is_private BOOLEAN DEFAULT FALSE,
                created_at TEXT,
                updated_at TEXT,
                pushed_at TEXT,
                topics TEXT,
                last_synced TEXT NOT NULL
            )
            """
        )

        # Ensure homepage_url exists on existing databases
        cols = {row[1] for row in cursor.execute("PRAGMA table_info(repositories)").fetchall()}
        if "homepage_url" not in cols:
            cursor.execute("ALTER TABLE repositories ADD COLUMN homepage_url TEXT")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS language_stats (
                language TEXT PRIMARY KEY,
                count INTEGER NOT NULL,
                percentage REAL NOT NULL,
                last_updated TEXT NOT NULL
            )
            """
        )

        self.conn.commit()
        print(f"Database initialized at {self.db_path}")

    def fetch_repositories(self) -> List[Dict[str, Any]]:
        """Fetch all owned public non-fork repositories using GitHub CLI."""
        print(f"Fetching public source repositories for {USERNAME}...")

        try:
            cmd = [
                "gh",
                "repo",
                "list",
                USERNAME,
                "--visibility",
                "public",
                "--source",
                "--limit",
                "1000",
                "--json",
                "name,description,url,homepageUrl,primaryLanguage,repositoryTopics,stargazerCount,forkCount,isFork,isPrivate,createdAt,updatedAt,pushedAt",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            repos_data = json.loads(result.stdout)
            # Defensive filter to ensure only public, non-fork repos are stored
            repos_data = [
                r for r in repos_data if not r.get("isPrivate", False) and not r.get("isFork", False)
            ]

            print(f"Found {len(repos_data)} public source repositories")
            return repos_data

        except subprocess.CalledProcessError as e:
            print(f"Error fetching repositories: {e}")
            print(f"Error output: {e.stderr}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            sys.exit(1)

    def update_repository(self, repo_data: Dict[str, Any]):
        """Update or insert a repository in the database."""
        cursor = self.conn.cursor()

        topics = []
        if repo_data.get("repositoryTopics"):
            topics = [topic["name"] for topic in repo_data["repositoryTopics"] if topic and topic.get("name")]
        topics_str = ",".join(topics) if topics else None

        primary_language = None
        if repo_data.get("primaryLanguage"):
            primary_language = repo_data["primaryLanguage"].get("name")

        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT OR REPLACE INTO repositories
            (name, description, url, homepage_url, primary_language, star_count, fork_count,
             is_fork, is_private, created_at, updated_at, pushed_at, topics, last_synced)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                repo_data["name"],
                repo_data.get("description") or "",
                repo_data["url"],
                repo_data.get("homepageUrl") or "",
                primary_language,
                repo_data.get("stargazerCount", 0),
                repo_data.get("forkCount", 0),
                False,
                False,
                repo_data.get("createdAt"),
                repo_data.get("updatedAt"),
                repo_data.get("pushedAt"),
                topics_str,
                now_iso,
            ),
        )

    def prune_stale_repositories(self, active_names: List[str]) -> int:
        """Remove deleted, private, or forked repos that are no longer active."""
        cursor = self.conn.cursor()
        if not active_names:
            return 0
        placeholders = ",".join("?" for _ in active_names)
        cursor.execute(f"DELETE FROM repositories WHERE name NOT IN ({placeholders})", active_names)
        removed = cursor.rowcount
        self.conn.commit()
        if removed:
            print(f"Pruned {removed} deleted/private/forked repositories from {self.db_path}")
        return removed

    def update_language_statistics(self):
        """Update language statistics in the database."""
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT primary_language, COUNT(*) as count
            FROM repositories
            WHERE primary_language IS NOT NULL AND primary_language != ''
              AND is_fork = 0 AND is_private = 0
            GROUP BY primary_language
            ORDER BY count DESC, primary_language ASC
            """
        )

        language_counts = cursor.fetchall()
        total_repos_with_language = sum(count for _, count in language_counts)

        cursor.execute("DELETE FROM language_stats")
        now_iso = datetime.now(timezone.utc).isoformat()
        for language, count in language_counts:
            percentage = (count / total_repos_with_language) * 100 if total_repos_with_language > 0 else 0.0
            cursor.execute(
                """
                INSERT INTO language_stats (language, count, percentage, last_updated)
                VALUES (?, ?, ?, ?)
                """,
                (language, count, percentage, now_iso),
            )

        self.conn.commit()
        print(f"Updated language statistics for {len(language_counts)} languages")

    def get_repository_stats(self) -> Dict[str, Any]:
        """Get overall repository statistics."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM repositories WHERE is_fork = 0 AND is_private = 0")
        total_repos = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(star_count) FROM repositories WHERE is_fork = 0 AND is_private = 0")
        total_stars = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(fork_count) FROM repositories WHERE is_fork = 0 AND is_private = 0")
        total_forks = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT name, star_count FROM repositories WHERE is_fork = 0 AND is_private = 0 ORDER BY star_count DESC, name ASC LIMIT 1"
        )
        most_starred = cursor.fetchone()

        return {
            "total_repos": total_repos,
            "total_stars": total_stars,
            "total_forks": total_forks,
            "most_starred": most_starred,
        }

    def sync_repositories(self):
        """Main method to sync all repositories and prune stale entries."""
        print("Starting repository synchronization...")

        repos_data = self.fetch_repositories()

        print("Updating database...")
        active_names = []
        for repo_data in repos_data:
            self.update_repository(repo_data)
            active_names.append(repo_data["name"])

        self.conn.commit()
        self.prune_stale_repositories(active_names)
        self.update_language_statistics()

        stats = self.get_repository_stats()
        print("\nSynchronization Summary:")
        print(f"  Total public repositories: {stats['total_repos']}")
        print(f"  Total stars: {stats['total_stars']}")
        print(f"  Total forks: {stats['total_forks']}")
        if stats["most_starred"]:
            print(f"  Most starred: {stats['most_starred'][0]} ({stats['most_starred'][1]} stars)")
        print("Repository synchronization completed.")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    try:
        os.makedirs("scripts", exist_ok=True)
        updater = RepoIndexUpdater()
        updater.sync_repositories()
        updater.close()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()