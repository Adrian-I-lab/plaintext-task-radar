# shellcheck shell=bash
# Shared checks for the pre-commit and commit-msg hooks.
#
# Terms come from the file named by $PORTFOLIO_DENYLIST, read at run time.
# One fixed string per line, matched case-insensitively. Lines starting with
# "#" and blank lines are ignored. The hooks never print a matched term or a
# matched secret, only where it was found. They fail closed: without a
# readable, non-empty term list, nothing is committed.
#
# Pure bash, grep, and sed, so the hooks run on Linux and macOS alike.

SCAN_HITS=0
SCAN_DIR=""
SCAN_TERMS=""

# Pairs of pattern name and extended regular expression.
SCAN_PATTERNS=(
  private-ipv4-10      '(^|[^0-9.])10(\.[0-9]{1,3}){3}([^0-9]|$)'
  private-ipv4-172     '(^|[^0-9.])172\.(1[6-9]|2[0-9]|3[01])(\.[0-9]{1,3}){2}([^0-9]|$)'
  private-ipv4-192     '(^|[^0-9.])192\.168(\.[0-9]{1,3}){2}([^0-9]|$)'
  shared-ipv4-100      '(^|[^0-9.])100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])(\.[0-9]{1,3}){2}([^0-9]|$)'
  home-path-unix       '/(home|Users)/[A-Za-z0-9._-]+'
  home-path-windows    '[A-Za-z]:\\Users\\[A-Za-z0-9._-]+'
  aws-access-key       'AKIA[0-9A-Z]{16}'
  private-key-block    '-----BEGIN [A-Z ]*PRIVATE KEY-----'
  github-token         'gh[pousr]_[A-Za-z0-9]{20,}'
  github-fine-token    'github_pat_[A-Za-z0-9_]{20,}'
  api-key-sk           'sk-[A-Za-z0-9_-]{20,}'
  slack-token          'xox[abprs]-[A-Za-z0-9-]{10,}'
  secret-assignment    '([Aa][Pp][Ii][_-]?[Kk][Ee][Yy]|[Ss][Ee][Cc][Rr][Ee][Tt]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Tt][Oo][Kk][Ee][Nn])["'\'']?[[:space:]]*[:=][[:space:]]*["'\''][A-Za-z0-9/+_.=-]{16,}["'\'']'
)

SCAN_EMAIL_RE='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
# Reserved example domains (RFC 2606), GitHub noreply addresses, and the
# co-author trailer address are the only addresses allowed.
SCAN_EMAIL_OK='@(users\.noreply\.github\.com|([A-Za-z0-9-]+\.)*example\.(com|org|net))$|^noreply@anthropic\.com$'

scan_die() {
  printf '%s: %s\n' "$SCAN_HOOK" "$1" >&2
  printf '%s: commit refused (the hook fails closed).\n' "$SCAN_HOOK" >&2
  exit 1
}

scan_report() {
  printf '%s: %s\n' "$SCAN_HOOK" "$1" >&2
  SCAN_HITS=$((SCAN_HITS + 1))
}

scan_init() {
  [ -n "${PORTFOLIO_DENYLIST:-}" ] || scan_die "PORTFOLIO_DENYLIST is not set"
  [ -f "$PORTFOLIO_DENYLIST" ] && [ -r "$PORTFOLIO_DENYLIST" ] ||
    scan_die "PORTFOLIO_DENYLIST does not name a readable file"
  SCAN_DIR=$(mktemp -d) || scan_die "cannot create a temporary directory"
  trap 'rm -rf "$SCAN_DIR"' EXIT
  SCAN_TERMS="$SCAN_DIR/terms"
  tr -d '\r' < "$PORTFOLIO_DENYLIST" |
    grep -v -E '^[[:space:]]*(#|$)' |
    sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' > "$SCAN_TERMS"
  [ -s "$SCAN_TERMS" ] || scan_die "the denylist holds no terms"
}

# scan_file LABEL PATH: report every problem in PATH, naming it LABEL.
scan_file() {
  local label=$1 path=$2 out rc line i addr
  out=$(grep -a -n -F -i -f "$SCAN_TERMS" -- "$path")
  rc=$?
  [ "$rc" -le 1 ] || scan_die "grep failed while scanning $label"
  while IFS= read -r line; do
    [ -n "$line" ] && scan_report "$label:${line%%:*}: denylist hit"
  done <<< "$out"

  for ((i = 0; i < ${#SCAN_PATTERNS[@]}; i += 2)); do
    out=$(grep -a -n -E -e "${SCAN_PATTERNS[i + 1]}" -- "$path")
    rc=$?
    [ "$rc" -le 1 ] || scan_die "grep failed while scanning $label"
    while IFS= read -r line; do
      [ -n "$line" ] && scan_report "$label:${line%%:*}: secret pattern ${SCAN_PATTERNS[i]}"
    done <<< "$out"
  done

  out=$(grep -a -n -o -E -e "$SCAN_EMAIL_RE" -- "$path")
  rc=$?
  [ "$rc" -le 1 ] || scan_die "grep failed while scanning $label"
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    addr=${line#*:}
    if ! printf '%s\n' "$addr" | grep -q -i -E -e "$SCAN_EMAIL_OK"; then
      scan_report "$label:${line%%:*}: secret pattern email-address"
    fi
  done <<< "$out"
}

scan_finish() {
  if [ "$SCAN_HITS" -gt 0 ]; then
    printf '%s: %d problem(s) found; commit refused. Fix the content, not the hook.\n' \
      "$SCAN_HOOK" "$SCAN_HITS" >&2
    exit 1
  fi
  exit 0
}
