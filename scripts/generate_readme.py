#!/usr/bin/env python3
"""
README & Web Catalog Data Generator

Generates a clean Markdown README.md (with valid blank lines before tables)
and exports data/repos.json for the interactive GitHub Pages web catalog.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

LANG_COLORS = {
    "Go": "#00ADD8",
    "Python": "#3572A5",
    "Java": "#B07219",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "C": "#6E7681",
    "C#": "#178600",
    "C++": "#F34B7D",
    "Kotlin": "#A97BFF",
    "Shell": "#89E051",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "Vim Script": "#199F4B",
    "Dockerfile": "#384D54",
    "Other": "#64748B",
}


def clean_text(text: str) -> str:
    return (text or "").replace("\u2014", " - ").replace("\u2013", "-").strip()


def classify_repo(repo: Dict[str, Any]) -> str:
    topics = (repo.get("topics") or "").lower()
    description = (repo.get("description") or "").lower()
    name = (repo.get("name") or "").lower()
    language = (repo.get("primary_language") or "").lower()
    blob = f"{name} {description} {topics}"

    if any(k in blob for k in ["kubernetes", "k8s", "docker", "opentelemetry", "otel", "prometheus", "grafana", "observability", "monitoring", "podbeacon", "otelviz", "logstream", "telemetry"]):
        return "Cloud & Observability"
    if any(k in blob for k in ["raft", "consensus", "saga", "distributed", "retry", "scheduler", "cron", "load", "lps", "balancer", "rabbitmq", "queue", "pubsub", "concurrency", "caching"]):
        return "Distributed Systems"
    if any(k in blob for k in ["security", "auth", "oauth", "oidc", "jwt", "encryption", "ssl", "tls"]):
        return "Security & Auth"
    if any(k in blob for k in ["api", "backend", "server", "microservice", "grpc", "connectrpc", "springboot", "spring-boot", "express", "starter"]):
        return "Backend & APIs"
    if any(k in blob for k in ["react", "frontend", "web-app", "visualizer", "demo", "portfolio", "github.io", "ui", "html", "css", "mermaid"]):
        return "Frontend & Demos"
    if language in {"kotlin", "c"} or any(k in blob for k in ["android", "mobile", "kotlin", "kernel", "sbunix", "fuse", "gtk4", "linux", "googlysync"]):
        return "Systems & Desktop/Mobile"
    if any(k in blob for k in ["data", "analysis", "analytics", "database", "sql", "duckdb", "ai", "ml", "tensorflow", "audio", "workout"]):
        return "Data & AI"
    if any(k in blob for k in ["learn", "tutorial", "example", "study", "practice", "notes", "guide", "tricks", "dotfiles", "config", "leetcode", "interview", "algorithms"]):
        return "Learning & Utilities"
    return "Other Projects"


class ReadmeGenerator:
    def __init__(self, db_path: str = "index.db", output_path: str = "README.md", json_path: str = "data/repos.json"):
        self.db_path = db_path
        self.output_path = output_path
        self.json_path = json_path

        if not os.path.exists(db_path):
            print(f"Database file {db_path} not found!")
            sys.exit(1)

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_all_public_repos(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cols = {row[1] for row in cursor.execute("PRAGMA table_info(repositories)").fetchall()}
        hp_select = "homepage_url" if "homepage_url" in cols else "'' AS homepage_url"
        cursor.execute(
            f"""
            SELECT name, description, url, {hp_select}, primary_language,
                   star_count, fork_count, topics, created_at, updated_at, pushed_at
            FROM repositories
            WHERE is_fork = 0 AND is_private = 0
            ORDER BY star_count DESC, pushed_at DESC, name ASC
            """
        )

        repos = []
        for row in cursor.fetchall():
            item = {
                "name": row["name"],
                "description": clean_text(row["description"] or ""),
                "url": row["url"],
                "homepage_url": (row["homepage_url"] or "").strip(),
                "primary_language": row["primary_language"] or "",
                "star_count": row["star_count"] or 0,
                "fork_count": row["fork_count"] or 0,
                "topics": row["topics"] or "",
                "created_at": (row["created_at"] or "")[:10],
                "updated_at": (row["updated_at"] or "")[:10],
                "pushed_at": (row["pushed_at"] or "")[:10],
            }
            item["category"] = classify_repo(item)
            repos.append(item)
        return repos

    def get_language_stats(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT language, count, percentage
            FROM language_stats
            ORDER BY count DESC, language ASC
            """
        )
        return [
            {
                "language": row[0],
                "count": row[1],
                "percentage": round(float(row[2]), 1),
                "color": LANG_COLORS.get(row[0], "#29B5E8"),
            }
            for row in cursor.fetchall()
        ]

    def generate_table(self, repos: List[Dict[str, Any]], include_language: bool = False) -> str:
        if not repos:
            return "\n_No repositories found._\n\n"

        if include_language:
            header = "\n| S.No | Repository | Description | Language | Stars | Forks |\n"
            separator = "|------|------------|-------------|----------|-------|-------|\n"
        else:
            header = "\n| S.No | Repository | Description | Stars | Forks |\n"
            separator = "|------|------------|-------------|-------|-------|\n"

        rows = [header, separator]
        for i, repo in enumerate(repos, 1):
            name_link = f"[{repo['name']}]({repo['url']})"
            desc = repo["description"]
            if len(desc) > 100:
                desc = desc[:97].rstrip() + "..."
            desc = desc.replace("|", "\\|")
            if include_language:
                lang = repo["primary_language"] or "N/A"
                rows.append(f"| {i} | {name_link} | {desc} | {lang} | {repo['star_count']} | {repo['fork_count']} |\n")
            else:
                rows.append(f"| {i} | {name_link} | {desc} | {repo['star_count']} | {repo['fork_count']} |\n")

        rows.append("\n")
        return "".join(rows)

    def export_web_json(self, repos: List[Dict[str, Any]], language_stats: List[Dict[str, Any]]):
        out_path = Path(self.json_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        now_utc = datetime.now(timezone.utc)

        total_stars = sum(r["star_count"] for r in repos)
        total_forks = sum(r["fork_count"] for r in repos)
        live_demos = sum(1 for r in repos if r["homepage_url"])

        categories_count: Dict[str, int] = {}
        for r in repos:
            cat = r["category"]
            categories_count[cat] = categories_count.get(cat, 0) + 1

        payload = {
            "updated_date": now_utc.strftime("%Y-%m-%d"),
            "updated_utc": now_utc.strftime("%Y-%m-%d %H:%M UTC"),
            "stats": {
                "total_repos": len(repos),
                "total_stars": total_stars,
                "total_forks": total_forks,
                "total_languages": len(language_stats),
                "live_demos": live_demos,
            },
            "languages": language_stats,
            "categories": [
                {"name": name, "count": count}
                for name, count in sorted(categories_count.items(), key=lambda x: (-x[1], x[0]))
            ],
            "repos": [
                {
                    "name": r["name"],
                    "description": r["description"],
                    "url": r["url"],
                    "demo": r["homepage_url"],
                    "language": r["primary_language"] or "Other",
                    "language_color": LANG_COLORS.get(r["primary_language"] or "Other", "#29B5E8"),
                    "stars": r["star_count"],
                    "forks": r["fork_count"],
                    "topics": [t.strip() for t in r["topics"].split(",") if t.strip()],
                    "category": r["category"],
                    "pushed_at": r["pushed_at"],
                    "created_at": r["created_at"],
                }
                for r in repos
            ],
        }

        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Exported web catalog data to {self.json_path} ({len(repos)} repos)")

    def generate_readme(self):
        print("Generating README.md and data/repos.json...")
        repos = self.get_all_public_repos()
        language_stats = self.get_language_stats()
        self.export_web_json(repos, language_stats)

        total_stars = sum(r["star_count"] for r in repos)
        now_utc = datetime.now(timezone.utc)

        content: List[str] = []
        content.append("# Repository Index\n\n")
        content.append(
            "A comprehensive, auto-synced catalog of my public GitHub repositories. "
            "Browse the interactive web catalog at [sandeepkv93.github.io/repo-index](https://sandeepkv93.github.io/repo-index/) "
            "or return to [sandeepkv93.github.io](https://sandeepkv93.github.io/).\n\n"
        )
        content.append(
            f"**Total Public Repositories:** {len(repos)} | "
            f"**Total Stars:** {total_stars} | "
            f"**Last Updated:** {now_utc.strftime('%B %d, %Y')}\n\n"
        )
        content.append("---\n\n")

        if language_stats:
            content.append("## Repository Statistics\n\n")
            content.append("| Language | Count | Percentage |\n")
            content.append("|----------|-------|------------|\n")
            for lang_stat in language_stats[:10]:
                content.append(
                    f"| {lang_stat['language']} | {lang_stat['count']} | {lang_stat['percentage']:.1f}% |\n"
                )
            content.append("\n---\n\n")

        content.append("## Repositories by Programming Language\n\n")
        major_languages = [ls for ls in language_stats if ls["count"] > 2]
        for lang_stat in major_languages:
            lang = lang_stat["language"]
            lang_repos = [r for r in repos if r["primary_language"] == lang]
            if lang_repos:
                content.append(f"### {lang} Projects ({len(lang_repos)})\n")
                content.append(self.generate_table(lang_repos))

        other_lang_names = {ls["language"] for ls in major_languages}
        other_repos = [r for r in repos if r["primary_language"] not in other_lang_names]
        if other_repos:
            content.append(f"### Other & Multi-Language Projects ({len(other_repos)})\n")
            content.append(self.generate_table(other_repos, include_language=True))

        content.append("---\n\n")
        content.append("## Repositories by Category\n\n")
        by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for r in repos:
            by_cat.setdefault(r["category"], []).append(r)

        for category, cat_repos in sorted(by_cat.items(), key=lambda x: (-len(x[1]), x[0])):
            content.append(f"### {category} ({len(cat_repos)})\n")
            content.append(self.generate_table(cat_repos, include_language=True))

        top_starred = [r for r in repos if r["star_count"] > 0][:10]
        if top_starred:
            content.append("---\n\n")
            content.append("## Top Starred Repositories\n\n")
            content.append("| Repository | Stars | Language | Description |\n")
            content.append("|------------|-------|----------|-------------|\n")
            for repo in top_starred:
                name_link = f"[{repo['name']}]({repo['url']})"
                desc = repo["description"]
                if len(desc) > 85:
                    desc = desc[:82].rstrip() + "..."
                desc = desc.replace("|", "\\|")
                lang = repo["primary_language"] or "N/A"
                content.append(f"| {name_link} | {repo['star_count']} | {lang} | {desc} |\n")
            content.append("\n")

        content.append("---\n\n")
        content.append("## Automation\n\n")
        content.append("This catalog is updated automatically every day via GitHub Actions:\n\n")
        content.append("- Fetches public non-fork repositories via GitHub CLI and prunes deleted repositories\n")
        content.append("- Updates `index.db` and exports `data/repos.json` for the interactive GitHub Pages catalog\n")
        content.append("- Regenerates `README.md` with current statistics\n\n")
        content.append(f"*Last automated update: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}*\n")

        Path(self.output_path).write_text("".join(content), encoding="utf-8")
        print(f"README.md generated successfully at {self.output_path}")

    def close(self):
        if self.conn:
            self.conn.close()


def main():
    try:
        generator = ReadmeGenerator()
        generator.generate_readme()
        generator.close()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()