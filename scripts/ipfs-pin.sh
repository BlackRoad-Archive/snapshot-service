#!/usr/bin/env bash
# BlackRoad Archive - IPFS Pinning for Snapshot Manifests
set -euo pipefail
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ARCHIVE_DIR="${ARCHIVE_DIR:-$HOME/.blackroad/archive}"
PIN_DB="${ARCHIVE_DIR}/ipfs-pins.json"
log()  { echo -e "${GREEN}OK${NC} $1"; }
info() { echo -e "${CYAN}->$NC $1"; }
err()  { echo -e "${RED}ERR${NC} $1" >&2; exit 1; }

detect_backend() {
  command -v ipfs >/dev/null 2>&1 && ipfs id >/dev/null 2>&1 && echo kubo && return
  command -v w3 >/dev/null 2>&1 && echo web3storage && return
  echo none
}

cmd_pin() {
  local backend
  backend=$(detect_backend)
  [ "$backend" = "none" ] && err "No IPFS backend. Install Kubo or w3cli"
  info "Backend: $backend"
  mkdir -p "$ARCHIVE_DIR"
  [ -f "$PIN_DB" ] || echo '{"pins":[]}' > "$PIN_DB"
  for f in "$ARCHIVE_DIR"/*.json; do
    [ -f "$f" ] || continue
    [ "$f" = "$PIN_DB" ] && continue
    if [ "$backend" = "kubo" ]; then
      cid=$(ipfs add -q "$f")
      ipfs pin add "$cid" >/dev/null
    else
      cid=$(w3 up "$f" --no-wrap 2>/dev/null | grep -oE 'bafy[a-z0-9]+' | head -1)
    fi
    [ -z "${cid:-}" ] && continue
    log "$f -> ipfs://$cid"
    python3 -c "
import json; from datetime import datetime
db=json.load(open('$PIN_DB'))
db['pins'].append({'file':'$(basename $f)','cid':'$cid','ts':datetime.utcnow().isoformat()+'Z'})
json.dump(db,open('$PIN_DB','w'),indent=2)"
  done
}

cmd_list() {
  [ -f "$PIN_DB" ] || { echo "No pins yet"; return; }
  python3 -c "import json; [print(p['cid'][:20]+'...', p['file']) for p in json.load(open('$PIN_DB'))['pins']]"
}

case "${1:-pin}" in
  pin)  cmd_pin ;;
  list) cmd_list ;;
  *)    echo "Usage: $0 [pin|list]" ;;
esac
