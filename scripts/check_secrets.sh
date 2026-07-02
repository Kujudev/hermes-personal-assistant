#!/usr/bin/env bash
# GR-SEC-03: fail if likely secrets are committed to the repository.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PATTERNS=(
  'sk-[A-Za-z0-9]{20,}'
  'AKIA[0-9A-Z]{16}'
  'BEGIN (RSA |OPENSSH )?PRIVATE KEY'
  'deepseek[_-]?api[_-]?key\s*=\s*["\x27][^"\x27]{8,}'
  'whatsapp[_-]?token\s*=\s*["\x27][^"\x27]{8,}'
)

FOUND=0
while IFS= read -r -d '' file; do
  for pattern in "${PATTERNS[@]}"; do
    if grep -qE "$pattern" "$file"; then
      echo "Potential secret in $file (pattern: $pattern)"
      FOUND=1
    fi
  done
done < <(find . -type f \
  ! -path './.git/*' \
  ! -path './.venv/*' \
  ! -name 'check_secrets.sh' \
  ! -name '*.md' \
  -print0)

if [[ "$FOUND" -ne 0 ]]; then
  echo "GR-SEC-03 FAILED: potential secrets detected"
  exit 1
fi

echo "GR-SEC-03 passed: no secret patterns found"
exit 0
