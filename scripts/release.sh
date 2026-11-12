#!/usr/bin/env bash
# Cut a release from main: pick the version, close [Unreleased], commit, push, tag.
#
#     scripts/release.sh patch      # 0.9.7 -> 0.9.8
#     scripts/release.sh minor      # 0.9.7 -> 0.10.0
#     scripts/release.sh major      # 0.9.7 -> 1.0.0
#
# The part is chosen here, at release time, because only now is it known what went in:
# entries accumulate under `## [Unreleased]`, which claims no number. The pushed tag is
# what the release pipeline builds and deploys.
#
# One command, because the order matters and git cannot enforce it: main reaches the
# remote before the tag does, so a tag never names a commit main lacks. A refusal before
# the commit leaves the tree untouched; a failed push says how to finish by hand.
set -euo pipefail

part="${1:-}"
case "$part" in
  patch | minor | major) ;;
  *)
    echo "usage: ${0##*/} patch|minor|major   (what this release is)" >&2
    exit 2
    ;;
esac

cd "$(git rev-parse --show-toplevel)"

# A dirty tree would tag a state nobody can check out again.
if [ -n "$(git status --porcelain)" ]; then
  echo "the working tree is dirty: commit first" >&2
  exit 1
fi

branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$branch" != main ]; then
  echo "releases are cut from main, not '$branch': merge the PR first" >&2
  exit 1
fi

# What is released must already be on origin/main: `git push <tag>` carries the commits
# along, so a tag on local-only history would publish code main does not have.
if ! git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
  echo "HEAD is not on origin/main: push first (or 'git fetch' if the ref is stale)" >&2
  exit 1
fi

# Only a tree `scripts/pre_release_qa.sh` passed may be tagged: its stamp holds the tree
# hash, so a squash onto the same tree keeps it. SKIP_PRERELEASE_QA=1 is for a hotfix that
# cannot wait for the run; the tag still has CI's checks behind it.
stamp="$(git rev-parse --path-format=absolute --git-path pre_release_qa.ok)"
if [ "${SKIP_PRERELEASE_QA:-}" = 1 ]; then
  echo "SKIP_PRERELEASE_QA=1: releasing without the pre-release run" >&2
elif [ "$(cat "$stamp" 2>/dev/null)" != "$(git rev-parse 'HEAD^{tree}')" ]; then
  echo "no green pre-release run for this tree: run scripts/pre_release_qa.sh first" >&2
  exit 1
fi

# Everything is validated before anything is written; this also refuses an empty [Unreleased].
version="$(python3 scripts/prepare_release.py "$part" --check)"
tag="v$version"
if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
  echo "$tag already exists: tags are immutable, release the next version instead" >&2
  exit 1
fi

python3 scripts/prepare_release.py "$part" >/dev/null
git add pyproject.toml uv.lock CHANGELOG.md
git commit -q -m "chore(release): $version"

# The check the pipeline runs on the tag, asked here so a bad section costs a second,
# not a failed pipeline. Its output is the release notes: reading them now is the review.
echo "── release notes for $tag ──────────────────────────────"
python3 scripts/release_from_tag.py "$tag"
echo "─────────────────────────────────────────────────────────"

# Branch before tag, for the reason above. The release commit is made by now, so a rerun
# would release the next version: a failed push is finished by hand instead.
if ! git push -q origin main; then
  echo "pushing main failed; finish by hand:" >&2
  echo "  git push origin main && git tag -a $tag -m $tag && git push origin $tag" >&2
  exit 1
fi
git tag -a "$tag" -m "$tag"
if ! git push -q origin "$tag"; then
  echo "pushing the tag failed; finish by hand: git push origin $tag" >&2
  exit 1
fi

echo "released $tag · the pipeline builds and deploys it · [Unreleased] is open again"
