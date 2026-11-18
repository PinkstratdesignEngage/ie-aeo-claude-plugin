#!/usr/bin/env bash
# Controlla che il repo locale sia allineato con GitLab e lo comunica a Claude.
#
# Usato dagli hook di .claude/settings.json:
#   - SessionStart: controlla sempre (--sempre);
#   - UserPromptSubmit: controlla solo se dall'ultimo prompt è passata più di un'ora.
#
# Non modifica nulla: fa solo `git fetch` e confronta. Il pull lo propone Claude,
# chiedendo conferma, secondo le regole di CLAUDE.md.

set -u
EVENTO="UserPromptSubmit"
SEMPRE=0
SOGLIA=3600
for a in "$@"; do
  case "$a" in
    --sempre) SEMPRE=1 ;;
    --evento=*) EVENTO="${a#--evento=}" ;;
  esac
done

cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null) || exit 0

# Timestamp dell'ultimo prompt, dentro .git così non finisce nel repo
STAMP="$GIT_DIR/claude-ultimo-prompt"
ORA=$(date +%s)
ULTIMO=$(cat "$STAMP" 2>/dev/null || echo 0)
echo "$ORA" > "$STAMP"
if [ "$SEMPRE" -eq 0 ] && [ $((ORA - ULTIMO)) -lt "$SOGLIA" ]; then
  exit 0
fi

git remote get-url origin >/dev/null 2>&1 || exit 0
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) || exit 0

if git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=15 fetch -q origin 2>/dev/null; then
  read -r AVANTI INDIETRO < <(git rev-list --left-right --count "HEAD...$UPSTREAM" 2>/dev/null || echo "0 0")
  MODIFICATI=$(git status --porcelain --untracked-files=no | wc -l | tr -d ' ')
  NUOVI=$(git status --porcelain | grep -c '^??' || true)
  ULTIMI=$(git log --format='%an: %s' "HEAD..$UPSTREAM" 2>/dev/null | head -5 | sed 's/^/  - /')

  if [ "$INDIETRO" -eq 0 ] && [ "$AVANTI" -eq 0 ]; then
    STATO="allineato"
    MSG="Repo locale allineato con GitLab ($UPSTREAM)."
  else
    STATO="disallineato"
    MSG="Repo locale NON allineato con GitLab ($UPSTREAM): $INDIETRO commit da scaricare, $AVANTI commit locali non pubblicati, $MODIFICATI file modificati non salvati in un commit, $NUOVI file nuovi."
    if [ "$INDIETRO" -gt 0 ]; then
      MSG="$MSG
Ultimi commit su GitLab non ancora in locale:
$ULTIMI
Prima di modificare qualsiasi file, avvisa l'utente e proponi di allinearsi con 'git pull --rebase'. Se ci sono file modificati non salvati, proponi prima un commit. Non sovrascrivere le modifiche dei colleghi: in caso di conflitto conserva entrambe le versioni e chiedi."
    fi
    if [ "$AVANTI" -gt 0 ]; then
      MSG="$MSG
Ci sono commit locali non ancora su GitLab: ricordalo all'utente e chiedi se pubblicarli."
    fi
  fi
else
  STATO="non verificato"
  MSG="Non è stato possibile contattare GitLab per verificare l'allineamento del repo. Avvisa l'utente prima di modificare file."
fi

python3 - "$EVENTO" "$STATO" "$MSG" <<'PY'
import json, sys
evento, stato, msg = sys.argv[1], sys.argv[2], sys.argv[3]
out = {"hookSpecificOutput": {"hookEventName": evento, "additionalContext": "[Controllo allineamento con GitLab] " + msg}}
if stato != "allineato":
    out["systemMessage"] = msg.splitlines()[0]
print(json.dumps(out, ensure_ascii=False))
PY
