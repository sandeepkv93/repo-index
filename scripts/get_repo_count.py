#!/usr/bin/env python3
"""
Get repository count for commit messages
"""

import sqlite3
import sys

def get_repo_count():
    """Get total repository count."""
    try:
        conn = sqlite3.connect('index.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM repositories WHERE is_fork = 0')
        count = cursor.fetchone()[0]
        conn.close()
        print(count)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    get_repo_count()