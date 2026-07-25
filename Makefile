# GitHub Repo Curator Makefile

.PHONY: help gui audit audit-5commits audit-raw setup-repos all

help:
	@echo "GitHub Repo Curator Commands:"
	@echo "  make gui             - Launch the interactive Web GUI Dashboard on http://localhost:8080"
	@echo "  make audit           - Run full visual CLI audit table"
	@echo "  make audit-5commits  - Output repo names with < 5 commits directly to target_repos.txt"
	@echo "  make audit-raw       - Print raw list of all repo names to stdout (ideal for piping / wl-copy)"
	@echo "  make setup-repos     - Publish and configure repos listed in target_repos.txt"
	@echo "  make all             - Run full CLI audit and setup"

gui:
	@python3 app.py

audit:
	@python3 audit.py

audit-5commits:
	@python3 audit.py --5commits --raw > target_repos.txt
	@echo "Saved repositories with < 5 commits to target_repos.txt:"
	@cat target_repos.txt

audit-raw:
	@python3 audit.py --raw

setup-repos:
	@python3 setup_repos.py -f target_repos.txt

all: audit setup-repos
