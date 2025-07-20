#!/usr/bin/env python3
"""
Repository Index Updater

This script fetches all GitHub repositories using the GitHub CLI and updates
a SQLite database with repository information.
"""

import sqlite3
import json
import subprocess
import sys
from datetime import datetime
from typing import List, Dict, Any
import os

class RepoIndexUpdater:
    def __init__(self, db_path: str = "index.db"):
        """Initialize the repository index updater."""
        self.db_path = db_path
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        """Create database tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Create repositories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                url TEXT NOT NULL,
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
        ''')
        
        # Create language statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS language_stats (
                language TEXT PRIMARY KEY,
                count INTEGER NOT NULL,
                percentage REAL NOT NULL,
                last_updated TEXT NOT NULL
            )
        ''')
        
        self.conn.commit()
        print(f"✅ Database initialized at {self.db_path}")
    
    def fetch_repositories(self) -> List[Dict[str, Any]]:
        """Fetch all repositories using GitHub CLI."""
        print("🔍 Fetching repositories from GitHub...")
        
        try:
            # Use gh CLI to fetch repository data
            cmd = [
                "gh", "repo", "list", 
                "--limit", "1000",
                "--json", "name,description,url,primaryLanguage,repositoryTopics,stargazerCount,forkCount,isFork,isPrivate,createdAt,updatedAt,pushedAt"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            repos_data = json.loads(result.stdout)
            
            print(f"✅ Found {len(repos_data)} repositories")
            return repos_data
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error fetching repositories: {e}")
            print(f"❌ Error output: {e.stderr}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON response: {e}")
            sys.exit(1)
    
    def update_repository(self, repo_data: Dict[str, Any]):
        """Update or insert a repository in the database."""
        cursor = self.conn.cursor()
        
        # Extract repository topics
        topics = []
        if repo_data.get('repositoryTopics'):
            topics = [topic['name'] for topic in repo_data['repositoryTopics']]
        topics_str = ','.join(topics) if topics else None
        
        # Extract primary language
        primary_language = None
        if repo_data.get('primaryLanguage') and repo_data['primaryLanguage']:
            primary_language = repo_data['primaryLanguage']['name']
        
        # Prepare data
        repo_info = {
            'name': repo_data['name'],
            'description': repo_data.get('description', ''),
            'url': repo_data['url'],
            'primary_language': primary_language,
            'star_count': repo_data.get('stargazerCount', 0),
            'fork_count': repo_data.get('forkCount', 0),
            'is_fork': repo_data.get('isFork', False),
            'is_private': repo_data.get('isPrivate', False),
            'created_at': repo_data.get('createdAt'),
            'updated_at': repo_data.get('updatedAt'),
            'pushed_at': repo_data.get('pushedAt'),
            'topics': topics_str,
            'last_synced': datetime.now().isoformat()
        }
        
        # Insert or update repository
        cursor.execute('''
            INSERT OR REPLACE INTO repositories 
            (name, description, url, primary_language, star_count, fork_count, 
             is_fork, is_private, created_at, updated_at, pushed_at, topics, last_synced)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tuple(repo_info.values()))
    
    def update_language_statistics(self):
        """Update language statistics in the database."""
        cursor = self.conn.cursor()
        
        # Get language counts
        cursor.execute('''
            SELECT primary_language, COUNT(*) as count
            FROM repositories 
            WHERE primary_language IS NOT NULL AND primary_language != ''
            GROUP BY primary_language
            ORDER BY count DESC
        ''')
        
        language_counts = cursor.fetchall()
        total_repos_with_language = sum(count for _, count in language_counts)
        
        # Clear existing language stats
        cursor.execute('DELETE FROM language_stats')
        
        # Insert updated language stats
        for language, count in language_counts:
            percentage = (count / total_repos_with_language) * 100 if total_repos_with_language > 0 else 0
            cursor.execute('''
                INSERT INTO language_stats (language, count, percentage, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (language, count, percentage, datetime.now().isoformat()))
        
        self.conn.commit()
        print(f"✅ Updated language statistics for {len(language_counts)} languages")
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """Get overall repository statistics."""
        cursor = self.conn.cursor()
        
        # Total repositories
        cursor.execute('SELECT COUNT(*) FROM repositories')
        total_repos = cursor.fetchone()[0]
        
        # Total stars
        cursor.execute('SELECT SUM(star_count) FROM repositories')
        total_stars = cursor.fetchone()[0] or 0
        
        # Total forks
        cursor.execute('SELECT SUM(fork_count) FROM repositories')
        total_forks = cursor.fetchone()[0] or 0
        
        # Most starred repository
        cursor.execute('SELECT name, star_count FROM repositories ORDER BY star_count DESC LIMIT 1')
        most_starred = cursor.fetchone()
        
        return {
            'total_repos': total_repos,
            'total_stars': total_stars,
            'total_forks': total_forks,
            'most_starred': most_starred
        }
    
    def sync_repositories(self):
        """Main method to sync all repositories."""
        print("🚀 Starting repository synchronization...")
        
        # Fetch repositories from GitHub
        repos_data = self.fetch_repositories()
        
        # Update each repository in the database
        print("💾 Updating database...")
        for repo_data in repos_data:
            self.update_repository(repo_data)
        
        # Commit all changes
        self.conn.commit()
        
        # Update language statistics
        self.update_language_statistics()
        
        # Print summary
        stats = self.get_repository_stats()
        print(f"\n📊 Synchronization Summary:")
        print(f"   • Total repositories: {stats['total_repos']}")
        print(f"   • Total stars: {stats['total_stars']}")
        print(f"   • Total forks: {stats['total_forks']}")
        if stats['most_starred']:
            print(f"   • Most starred: {stats['most_starred'][0]} ({stats['most_starred'][1]} stars)")
        
        print(f"✅ Repository synchronization completed!")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

def main():
    """Main function."""
    try:
        # Create scripts directory if it doesn't exist
        os.makedirs('scripts', exist_ok=True)
        
        # Initialize updater
        updater = RepoIndexUpdater()
        
        # Sync repositories
        updater.sync_repositories()
        
        # Close database connection
        updater.close()
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()