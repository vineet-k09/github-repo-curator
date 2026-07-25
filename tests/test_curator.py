#!/usr/bin/env python3
"""
Test Suite for GitHub Repo Curator
Compatible with both pytest and python -m unittest.
"""

import json
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import app

class TestGitHubRepoCurator(unittest.TestCase):
    def setUp(self):
        self.test_db_path = os.path.join(os.path.dirname(__file__), 'test_cache.db')
        app.DB_PATH = self.test_db_path
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        app.init_db()

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_database_initialization(self):
        conn = app.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repo_cache'")
        table = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(table, "Table repo_cache should be created on init_db()")

    def test_get_all_cached_repos_empty(self):
        repos = app.get_all_cached_repos()
        self.assertEqual(len(repos), 0, "Initial cached repos list should be empty")

    def test_insert_and_get_cached_repos(self):
        conn = app.get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO repo_cache (
                name, full_name, description, visibility, is_private, language, homepage,
                stargazers_count, forks_count, pushed_at, topics, has_readme, has_license,
                commit_count, source_files, total_files, last_synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'test-repo', 'user/test-repo', 'Sample project', 'PUBLIC', 0, 'Python',
            'https://example.com', 5, 2, '2026-07-26', json.dumps(['pytest', 'python']),
            1, 1, 15, 10, 25, '2026-07-26 00:00:00'
        ))
        conn.commit()
        conn.close()

        repos = app.get_all_cached_repos()
        self.assertEqual(len(repos), 1)
        r = repos[0]
        self.assertEqual(r['name'], 'test-repo')
        self.assertFalse(r['is_private'])
        self.assertEqual(r['topics'], ['pytest', 'python'])
        self.assertEqual(r['commit_count'], 15)

    def test_pat_url_constant(self):
        self.assertIn("scopes=repo,delete_repo", app.PAT_CREATE_URL)
        self.assertTrue(app.PAT_CREATE_URL.startswith("https://github.com/settings/tokens/new"))

if __name__ == '__main__':
    unittest.main()
