#!/usr/bin/env python3
"""
Simple statistics extractor for GitHub Actions
"""

import sqlite3
import sys

def get_stats():
    """Get basic repository statistics."""
    try:
        conn = sqlite3.connect('index.db')
        cursor = conn.cursor()
        
        # Get statistics
        cursor.execute('SELECT COUNT(*) FROM repositories WHERE is_fork = 0')
        total_repos = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(star_count) FROM repositories WHERE is_fork = 0')
        total_stars = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(DISTINCT primary_language) FROM repositories WHERE primary_language IS NOT NULL AND primary_language != "" AND is_fork = 0')
        unique_languages = cursor.fetchone()[0]
        
        cursor.execute('SELECT name, star_count FROM repositories WHERE is_fork = 0 ORDER BY star_count DESC LIMIT 1')
        top_repo = cursor.fetchone()
        
        print(f'**Total Repositories:** {total_repos}')
        print(f'**Total Stars:** {total_stars}')
        print(f'**Programming Languages:** {unique_languages}')
        if top_repo and top_repo[1] > 0:
            print(f'**Most Starred:** {top_repo[0]} ({top_repo[1]} ⭐)')
        
        conn.close()
        
    except Exception as e:
        print(f'Error getting statistics: {e}')
        sys.exit(1)

if __name__ == "__main__":
    get_stats()