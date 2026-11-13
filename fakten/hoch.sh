#!/bin/bash
# kopiert fertige Videos ins Repo, ein Video pro Commit und Push
cd /home/claude/motojumpervideos
for t in /home/claude/fakten/videos/fakten_*.txt; do
  k=$(basename "$t" .txt); m="/home/claude/fakten/videos/$k.mp4"
  [ -f "$m" ] || continue
  cmp -s "$m" "fakten/videos/$k.mp4" && continue
  cp "$m" "$t" fakten/videos/
  git add "fakten/videos/$k.mp4" "fakten/videos/$k.txt"
  git diff --cached --quiet && continue
  git -c user.name=Claude -c user.email=noreply@anthropic.com commit -q -m "Add fact video ${k#fakten_}

Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_019injX524PHjhCd8qmaQPgg"
  git push -q origin main 2>/dev/null || { sleep 5; git push -q origin main 2>/dev/null || echo "PUSH FEHLER $k"; }
  echo "$k $(git rev-parse HEAD)" >> /home/claude/fakten/commits.txt
done
echo "im Repo: $(ls fakten/videos/*.mp4 | wc -l)"
