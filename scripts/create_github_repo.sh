#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/create_github_repo.sh [repo-name] [public|private]
REPO_NAME=${1:-Agent-Threads}
VISIBILITY=${2:-public}

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required. Install from https://github.com/cli/cli and authenticate with 'gh auth login'"
  exit 1
fi

git add .
git commit -m "Initial commit" || echo "No changes to commit"

echo "Creating GitHub repository '$REPO_NAME' with visibility '$VISIBILITY'..."
gh repo create "$REPO_NAME" --$VISIBILITY --source=. --remote=origin --push

echo "Repository created and pushed."
