#!/usr/bin/env python3
"""
README Generator

This script generates a comprehensive README.md file from the SQLite database
containing repository information.
"""

import sqlite3
import sys
from datetime import datetime
from typing import List, Dict, Any, Tuple
import os

class ReadmeGenerator:
    def __init__(self, db_path: str = "index.db", output_path: str = "README.md"):
        """Initialize the README generator."""
        self.db_path = db_path
        self.output_path = output_path
        self.conn = None
        
        if not os.path.exists(db_path):
            print(f"❌ Database file {db_path} not found!")
            sys.exit(1)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """Get overall repository statistics."""
        cursor = self.conn.cursor()
        
        # Total repositories
        cursor.execute('SELECT COUNT(*) FROM repositories WHERE is_fork = 0')
        total_repos = cursor.fetchone()[0]
        
        # Total stars
        cursor.execute('SELECT SUM(star_count) FROM repositories WHERE is_fork = 0')
        total_stars = cursor.fetchone()[0] or 0
        
        # Total forks
        cursor.execute('SELECT SUM(fork_count) FROM repositories WHERE is_fork = 0')
        total_forks = cursor.fetchone()[0] or 0
        
        return {
            'total_repos': total_repos,
            'total_stars': total_stars,
            'total_forks': total_forks
        }
    
    def get_language_stats(self) -> List[Dict[str, Any]]:
        """Get language statistics."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT language, count, percentage 
            FROM language_stats 
            ORDER BY count DESC
        ''')
        
        return [{'language': row[0], 'count': row[1], 'percentage': row[2]} 
                for row in cursor.fetchall()]
    
    def get_repositories_by_language(self, language: str) -> List[Dict[str, Any]]:
        """Get repositories for a specific programming language."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT name, description, url, star_count, fork_count, topics
            FROM repositories 
            WHERE primary_language = ? AND is_fork = 0
            ORDER BY star_count DESC, name ASC
        ''', (language,))
        
        repos = []
        for row in cursor.fetchall():
            repos.append({
                'name': row[0],
                'description': row[1] or '',
                'url': row[2],
                'star_count': row[3],
                'fork_count': row[4],
                'topics': row[5]
            })
        
        return repos
    
    def get_repositories_without_language(self) -> List[Dict[str, Any]]:
        """Get repositories without a primary language."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT name, description, url, star_count, fork_count, topics
            FROM repositories 
            WHERE (primary_language IS NULL OR primary_language = '') AND is_fork = 0
            ORDER BY star_count DESC, name ASC
        ''')
        
        repos = []
        for row in cursor.fetchall():
            repos.append({
                'name': row[0],
                'description': row[1] or '',
                'url': row[2],
                'star_count': row[3],
                'fork_count': row[4],
                'topics': row[5]
            })
        
        return repos
    
    def get_top_starred_repos(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top starred repositories."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT name, description, url, star_count, primary_language
            FROM repositories 
            WHERE is_fork = 0 AND star_count > 0
            ORDER BY star_count DESC, name ASC
            LIMIT ?
        ''', (limit,))
        
        repos = []
        for row in cursor.fetchall():
            repos.append({
                'name': row[0],
                'description': row[1] or '',
                'url': row[2],
                'star_count': row[3],
                'primary_language': row[4] or 'N/A'
            })
        
        return repos
    
    def categorize_repositories(self) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize repositories by topic/type."""
        categories = {
            'Backend Development': [],
            'Frontend Development': [],
            'DevOps & Infrastructure': [],
            'Mobile Development': [],
            'AI & Machine Learning': [],
            'Configuration & Utilities': [],
            'Learning & Documentation': [],
            'Data & Analytics': [],
            'Security': [],
            'Other Projects': []
        }
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT name, description, url, star_count, fork_count, primary_language, topics
            FROM repositories 
            WHERE is_fork = 0
            ORDER BY star_count DESC, name ASC
        ''')
        
        for row in cursor.fetchall():
            repo = {
                'name': row[0],
                'description': row[1] or '',
                'url': row[2],
                'star_count': row[3],
                'fork_count': row[4],
                'primary_language': row[5],
                'topics': row[6] or ''
            }
            
            # Categorize based on topics, description, and name
            topics = repo['topics'].lower()
            description = repo['description'].lower()
            name = repo['name'].lower()
            language = (repo['primary_language'] or '').lower()
            
            categorized = False
            
            # Backend Development
            if any(keyword in topics or keyword in description or keyword in name for keyword in 
                   ['api', 'backend', 'server', 'microservice', 'grpc', 'oauth', 'jwt', 'springboot', 'spring-boot', 'golang', 'express']):
                categories['Backend Development'].append(repo)
                categorized = True
            
            # Frontend Development
            elif any(keyword in topics or keyword in description or keyword in name for keyword in 
                     ['react', 'frontend', 'web-app', 'javascript', 'typescript', 'ui', 'html', 'css']):
                categories['Frontend Development'].append(repo)
                categorized = True
            
            # DevOps & Infrastructure
            elif any(keyword in topics or keyword in description or keyword in name for keyword in 
                     ['kubernetes', 'k8s', 'docker', 'deployment', 'infrastructure', 'observability', 'monitoring', 'prometheus', 'grafana']):
                categories['DevOps & Infrastructure'].append(repo)
                categorized = True
            
            # Mobile Development
            elif language == 'kotlin' or any(keyword in topics or keyword in description or keyword in name for keyword in 
                                              ['android', 'mobile', 'kotlin', 'swift', 'ios']):
                categories['Mobile Development'].append(repo)
                categorized = True
            
            # AI & Machine Learning
            elif any(keyword in topics or keyword in description or keyword in name for keyword in 
                     ['ai', 'ml', 'machine-learning', 'chatbot', 'nlp', 'tensorflow', 'pytorch', 'podcast', 'text-to-speech', 'metagpt']):
                categories['AI & Machine Learning'].append(repo)
                categorized = True
            
            # Configuration & Utilities
            elif any(keyword in topics or keyword in description or keyword in name for keyword in 
                     ['dotfiles', 'config', 'utility', 'scripts', 'automation', 'tools']):
                categories['Configuration & Utilities'].append(repo)
                categorized = True
            
            # Learning & Documentation
            elif any(keyword in topics or keyword in description or keyword in name for keyword in 
                     ['learn', 'tutorial', 'example', 'demo', 'study', 'practice', 'notes', 'documentation', 'concepts']):
                categories['Learning & Documentation'].append(repo)
                categorized = True
            
            # Data & Analytics
            elif any(keyword in topics or keyword in description or keyword in name for keyword in 
                     ['data', 'analysis', 'analytics', 'database', 'sql', 'covid', 'metrics']):
                categories['Data & Analytics'].append(repo)
                categorized = True
            
            # Security
            elif any(keyword in topics or keyword in description or keyword in name for keyword in 
                     ['security', 'auth', 'oauth', 'jwt', 'encryption', 'ssl', 'tls']):
                categories['Security'].append(repo)
                categorized = True
            
            # Default to Other Projects
            if not categorized:
                categories['Other Projects'].append(repo)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    def generate_table(self, repos: List[Dict[str, Any]], include_language: bool = False) -> str:
        """Generate a markdown table for repositories."""
        if not repos:
            return "_No repositories found._\n"
        
        # Table header
        if include_language:
            header = "| S.No | Repository | Description | Language | Stars | Forks |\n"
            separator = "|------|------------|-------------|----------|-------|-------|\n"
        else:
            header = "| S.No | Repository | Description | Stars | Forks |\n"
            separator = "|------|------------|-------------|-------|-------|\n"
        
        table = header + separator
        
        # Table rows
        for i, repo in enumerate(repos, 1):
            name_link = f"[{repo['name']}]({repo['url']})"
            description = repo['description'][:100] + "..." if len(repo['description']) > 100 else repo['description']
            description = description.replace('|', '\\|') if description else ''
            
            if include_language:
                language = repo.get('primary_language') or 'N/A'
                row = f"| {i} | {name_link} | {description} | {language} | {repo['star_count']} | {repo['fork_count']} |\n"
            else:
                row = f"| {i} | {name_link} | {description} | {repo['star_count']} | {repo['fork_count']} |\n"
            
            table += row
        
        return table + "\n"
    
    def generate_readme(self):
        """Generate the complete README.md file."""
        print("📝 Generating README.md...")
        
        # Get statistics
        stats = self.get_repository_stats()
        language_stats = self.get_language_stats()
        top_starred = self.get_top_starred_repos(10)
        categories = self.categorize_repositories()
        
        # Start building README content
        content = []
        
        # Header
        content.append("# 📚 Repository Index\n")
        content.append("A comprehensive index of all my GitHub repositories, categorized by programming language and topic.\n")
        content.append(f"**Total Repositories:** {stats['total_repos']}  ")
        content.append(f"**Total Stars:** {stats['total_stars']}  ")
        content.append(f"**Last Updated:** {datetime.now().strftime('%B %d, %Y')}\n")
        content.append("---\n")
        
        # Repository Statistics
        if language_stats:
            content.append("## 📊 Repository Statistics\n")
            content.append("| Language | Count | Percentage |\n")
            content.append("|----------|-------|------------|\n")
            
            for lang_stat in language_stats[:10]:  # Top 10 languages
                percentage = f"{lang_stat['percentage']:.1f}%"
                content.append(f"| {lang_stat['language']} | {lang_stat['count']} | {percentage} |\n")
            
            content.append("\n---\n")
        
        # Language-based sections
        content.append("## 🔤 Repositories by Programming Language\n")
        
        # Get major languages (more than 2 repos)
        major_languages = [ls for ls in language_stats if ls['count'] > 2]
        
        for lang_stat in major_languages:
            language = lang_stat['language']
            repos = self.get_repositories_by_language(language)
            
            if repos:
                # Language emoji mapping
                emoji_map = {
                    'Go': '🐹', 'Java': '☕', 'JavaScript': '🟨', 'Python': '🐍',
                    'C#': '🔷', 'TypeScript': '📘', 'Kotlin': '📱', 'Swift': '🍎',
                    'Rust': '🦀', 'C++': '⚡', 'C': '🔧', 'Ruby': '💎',
                    'PHP': '🐘', 'Dart': '🎯', 'Shell': '🐚', 'HTML': '🌐',
                    'CSS': '🎨', 'Vim Script': '✏️', 'Dockerfile': '🐳'
                }
                
                emoji = emoji_map.get(language, '📄')
                content.append(f"### {emoji} {language} Projects\n")
                content.append(self.generate_table(repos))
        
        # Projects without language
        no_lang_repos = self.get_repositories_without_language()
        if no_lang_repos:
            content.append("### 📄 Other Projects\n")
            content.append(self.generate_table(no_lang_repos))
        
        content.append("---\n")
        
        # Categorized sections
        content.append("## 🎯 Repositories by Category\n")
        
        category_emojis = {
            'Backend Development': '⚙️',
            'Frontend Development': '🎨',
            'DevOps & Infrastructure': '🚀',
            'Mobile Development': '📱',
            'AI & Machine Learning': '🤖',
            'Configuration & Utilities': '🔧',
            'Learning & Documentation': '📚',
            'Data & Analytics': '📊',
            'Security': '🔐',
            'Other Projects': '📦'
        }
        
        for category, repos in categories.items():
            if repos:
                emoji = category_emojis.get(category, '📦')
                content.append(f"### {emoji} {category}\n")
                content.append(self.generate_table(repos, include_language=True))
        
        # Top starred repositories
        if top_starred:
            content.append("---\n")
            content.append("## 🏆 Top Starred Repositories\n")
            content.append("| Repository | Stars | Language | Description |\n")
            content.append("|------------|-------|----------|-------------|\n")
            
            for repo in top_starred:
                name_link = f"[{repo['name']}]({repo['url']})"
                description = repo['description'][:80] + "..." if len(repo['description']) > 80 else repo['description']
                description = description.replace('|', '\\|') if description else ''
                content.append(f"| {name_link} | {repo['star_count']} | {repo['primary_language']} | {description} |\n")
            
            content.append("\n")
        
        # Key Technologies section
        content.append("---\n")
        content.append("## 🛠️ Key Technologies & Topics\n")
        
        # Extract most common topics
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT topics FROM repositories 
            WHERE topics IS NOT NULL AND topics != '' AND is_fork = 0
        ''')
        
        all_topics = {}
        for row in cursor.fetchall():
            topics = row[0].split(',')
            for topic in topics:
                topic = topic.strip()
                if topic:
                    all_topics[topic] = all_topics.get(topic, 0) + 1
        
        # Sort topics by frequency
        sorted_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_topics:
            content.append("### Most Common Topics\n")
            topic_list = []
            for topic, count in sorted_topics[:20]:  # Top 20 topics
                topic_list.append(f"`{topic}` ({count})")
            
            # Group topics in lines of 4
            for i in range(0, len(topic_list), 4):
                line_topics = topic_list[i:i+4]
                content.append(" • ".join(line_topics) + "\n")
            
            content.append("\n")
        
        # Footer
        content.append("---\n")
        content.append("## 🔄 Automation\n")
        content.append("This repository index is automatically updated daily using GitHub Actions. ")
        content.append("The automation:\n")
        content.append("- Fetches latest repository data using GitHub CLI\n")
        content.append("- Updates a SQLite database with repository information\n")
        content.append("- Regenerates this README.md with current statistics\n")
        content.append("- Commits changes if any updates are detected\n\n")
        content.append("*Last automated update: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC') + "*\n")
        
        # Write to file
        readme_content = "".join(content)
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✅ README.md generated successfully at {self.output_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

def main():
    """Main function."""
    try:
        generator = ReadmeGenerator()
        generator.generate_readme()
        generator.close()
        
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()