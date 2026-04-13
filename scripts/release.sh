#!/usr/bin/env bash
# Update version across all files that contain it.
# Usage: ./scripts/release.sh 0.9.0
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 0.9.0"
    exit 1
fi

VERSION="$1"

# Validate semver format
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
    echo "Error: '$VERSION' is not a valid semver version"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1. pyproject.toml
sed -i "s/^version = \".*\"/version = \"$VERSION\"/" "$REPO_ROOT/pyproject.toml"
echo "Updated pyproject.toml"

# 2. uv.lock (refresh after pyproject.toml change)
if command -v uv >/dev/null 2>&1; then
    (cd "$REPO_ROOT" && uv lock >/dev/null)
    echo "Updated uv.lock"
else
    echo "Warning: uv not found, skipping uv.lock refresh"
fi

# 3. Verify CHANGELOG.md has a section for this version
if ! grep -q "^## \[$VERSION\]" "$REPO_ROOT/CHANGELOG.md"; then
    echo ""
    echo "Warning: CHANGELOG.md has no section for [$VERSION]."
    echo "Add one before tagging:"
    echo "  ## [$VERSION] — $(date +%Y-%m-%d)"
fi

echo ""
echo "Version updated to $VERSION"
echo ""
echo "Next steps:"
echo "  1. Review changes:  git diff"
echo "  2. Commit:          git commit -am 'release: v$VERSION'"
echo "  3. Tag:             git tag v$VERSION"
echo "  4. Push:            git push origin main v$VERSION"
