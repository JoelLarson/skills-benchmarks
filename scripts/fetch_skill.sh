#!/usr/bin/env bash
# Fetch a skill from a git repo, gist/raw URL, or local dir/.skill, and normalize it
# into a --skills-dir-ready folder:  skills-eval/<name>/<name>/SKILL.md
# Prints the skills-dir path (skills-eval/<name>) as the final stdout line.
set -euo pipefail
cd "$(dirname "$0")/.."

SRC="${1:?usage: fetch_skill.sh <source> [name]}"
NAME="${2:-}"

derive_name() {
  local s="$1" b
  b="$(basename "${s%.git}")"
  b="${b%.skill}"; b="${b%.zip}"
  # gist ids / messy names -> kebab fallback
  echo "$b" | tr -c 'A-Za-z0-9._-' '-' | sed 's/-\+/-/g;s/^-//;s/-$//' | tr '[:upper:]' '[:lower:]'
}
[[ -z "$NAME" ]] && NAME="$(derive_name "$SRC")"
[[ -z "$NAME" ]] && NAME="skill"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
SKILL_MD=""   # path to the located SKILL.md
SKILL_ROOT="" # dir holding SKILL.md (to copy references/scripts alongside)

find_skill_md() {  # $1 = search root; prefer skills/*/SKILL.md, then root, then any
  local root="$1" f
  f="$(find "$root" -path '*/skills/*/SKILL.md' 2>/dev/null | head -1)"
  [[ -z "$f" && -f "$root/SKILL.md" ]] && f="$root/SKILL.md"
  [[ -z "$f" ]] && f="$(find "$root" -name SKILL.md 2>/dev/null | head -1)"
  echo "$f"
}

if [[ -d "$SRC" ]]; then
  SKILL_MD="$(find_skill_md "$SRC")"
elif [[ "$SRC" == *.skill || "$SRC" == *.zip ]]; then
  unzip -q "$SRC" -d "$WORK/unz"
  SKILL_MD="$(find_skill_md "$WORK/unz")"
elif [[ "$SRC" == *gist.github.com/* ]]; then
  # gist page URL -> raw of its (first) file
  curl -fsSL "${SRC%/}/raw" -o "$WORK/SKILL.md"
  SKILL_MD="$WORK/SKILL.md"
elif [[ "$SRC" == *.git || ( "$SRC" == https://github.com/* && "$(echo "$SRC" | awk -F/ '{print NF}')" -le 5 ) ]]; then
  git clone --depth 1 "$SRC" "$WORK/repo" >/dev/null 2>&1
  SKILL_MD="$(find_skill_md "$WORK/repo")"
elif [[ "$SRC" == http://* || "$SRC" == https://* ]]; then
  curl -fsSL "$SRC" -o "$WORK/SKILL.md"
  SKILL_MD="$WORK/SKILL.md"
else
  echo "fetch_skill: unrecognized source: $SRC" >&2
  exit 1
fi

if [[ -z "$SKILL_MD" || ! -f "$SKILL_MD" ]]; then
  echo "fetch_skill: no SKILL.md found in source: $SRC" >&2
  exit 1
fi
SKILL_ROOT="$(dirname "$SKILL_MD")"

DEST_ROOT="skills-eval/$NAME"          # this is the --skills-dir
DEST_SKILL="$DEST_ROOT/$NAME"          # one skill subfolder
rm -rf "$DEST_ROOT"
mkdir -p "$DEST_SKILL"
cp "$SKILL_MD" "$DEST_SKILL/SKILL.md"
# carry bundled resources if present alongside SKILL.md
for extra in references scripts assets; do
  [[ -d "$SKILL_ROOT/$extra" ]] && cp -r "$SKILL_ROOT/$extra" "$DEST_SKILL/"
done

echo "fetch_skill: wrote $DEST_SKILL/SKILL.md" >&2
echo "$DEST_ROOT"
