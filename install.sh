#!/usr/bin/env bash
# Installs the India trader skills for Claude Code: copies the in-* folders to ~/.claude/skills/
set -e
cd "$(dirname "$0")"
./build.sh
mkdir -p "$HOME/.claude/skills"
for d in in-*/; do
  rm -rf "$HOME/.claude/skills/${d%/}"
  cp -r "$d" "$HOME/.claude/skills/${d%/}"
done
echo "Installed $(ls -d in-*/ | wc -l) skills into $HOME/.claude/skills. Restart Claude Code, then type /in-"
