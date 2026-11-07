#!/usr/bin/env bash
# Smoke test cấu hình nginx của image production (FE-14) bằng docker, không cần
# backend/DB/LLM thật: build stage cuối của frontend/Dockerfile, chạy cùng backend
# giả (mock_backend.py, alias mạng `backend`) rồi kiểm bằng curl.
#
#   bash frontend/scripts/nginx-smoke/run.sh            # đầy đủ, ~4 phút (chờ timeout thật)
#   bash frontend/scripts/nginx-smoke/run.sh --quick    # bỏ các bước chờ dài
#   bash frontend/scripts/nginx-smoke/run.sh --no-build # dùng image đã build ($IMAGE)
#
# Biến môi trường: IMAGE (mặc định ptit-chatbot-frontend:nginx-smoke), PORT (18080).
# Cần: docker, curl, node (kiểm hash CSP của dist/index.html).
set -uo pipefail

usage() { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; }

QUICK=0
BUILD=1
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    --no-build) BUILD=0 ;;
    -h | --help) usage; exit 0 ;;
    *) echo "Tham số không hợp lệ: $arg" >&2; usage >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
IMAGE="${IMAGE:-ptit-chatbot-frontend:nginx-smoke}"
PORT="${PORT:-18080}"
BASE="http://127.0.0.1:$PORT"
SUFFIX="$$-$RANDOM"
NET="fe14-smoke-$SUFFIX"
MOCK="fe14-mock-$SUFFIX"
WEB="fe14-web-$SUFFIX"
TMP="$(mktemp -d)"

# Git Bash trên Windows tự đổi đối số dạng /đường/dẫn khi gọi docker.exe; tắt riêng cho docker.
dk() { MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker "$@"; }

PASS=0
FAIL=0
SKIP=0
cleanup() {
  if [ "$FAIL" -gt 0 ] && dk inspect "$MOCK" >/dev/null 2>&1; then
    echo "--- log nginx ---"; dk logs "$WEB" 2>&1 | tail -n 30
    echo "--- log mock ---"; dk logs "$MOCK" 2>&1 | tail -n 30
  fi
  dk rm -f "$MOCK" "$WEB" >/dev/null 2>&1
  dk network rm "$NET" >/dev/null 2>&1
  rm -rf "$TMP"
}
trap cleanup EXIT

pass() { PASS=$((PASS + 1)); echo "  PASS $*"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL $*"; }
skip() { SKIP=$((SKIP + 1)); echo "  SKIP $*"; }
section() { echo; echo "== $*"; }

# fetch <tệp header> <curl args...>: lưu header (bỏ \r), bỏ body.
fetch() {
  local out="$1"; shift
  curl -s -o /dev/null -D - "$@" | tr -d '\r' > "$out"
}
# Mã trạng thái cuối (bỏ qua 100 Continue).
status_of() { grep '^HTTP/' "$1" | tail -n 1 | cut -d' ' -f2; }
header_of() { grep -i "^$2:" "$1" | tail -n 1 | cut -d' ' -f2-; }

expect_status() { # <tệp header> <mã> <mô tả>
  local got; got="$(status_of "$1")"
  if [ "$got" = "$2" ]; then pass "$3 -> $got"; else fail "$3: cần $2, nhận '${got:-không có}'"; fi
}
expect_header() { # <tệp header> <tên> <regex giá trị> <mô tả>
  local got; got="$(header_of "$1" "$2")"
  if printf '%s' "$got" | grep -qE "^($3)\$"; then pass "$4: $2"; else fail "$4: $2 cần /$3/, nhận '${got:-không có}'"; fi
}
expect_no_header() { # <tệp header> <tên> <mô tả>
  local got; got="$(header_of "$1" "$2")"
  if [ -z "$got" ]; then pass "$3: không có $2"; else fail "$3: không được có $2 (nhận '$got')"; fi
}

COMMON_HEADERS=(
  "X-Content-Type-Options|nosniff"
  "Referrer-Policy|strict-origin-when-cross-origin"
  "X-Frame-Options|SAMEORIGIN"
  "Permissions-Policy|camera=\(\), microphone=\(\), geolocation=\(\), payment=\(\), usb=\(\)"
  "Cross-Origin-Opener-Policy|same-origin"
  "Server|nginx"
)
expect_security_headers() { # <tệp header> <page|api> <mô tả>
  local entry
  for entry in "${COMMON_HEADERS[@]}"; do
    expect_header "$1" "${entry%%|*}" "${entry#*|}" "$3"
  done
  if [ "$2" = page ]; then
    expect_header "$1" Content-Security-Policy "default-src 'self'; script-src 'self' 'sha256-[A-Za-z0-9+/=]+'; .*frame-ancestors 'self'" "$3"
  else
    expect_no_header "$1" Content-Security-Policy "$3"
  fi
}

section "Build image"
if [ "$BUILD" = 1 ]; then
  if ! (cd "$REPO_ROOT" && dk build -q -f frontend/Dockerfile -t "$IMAGE" . >/dev/null); then
    echo "Build thất bại" >&2; exit 1
  fi
  pass "docker build -f frontend/Dockerfile -> $IMAGE"
else
  skip "build (--no-build), dùng $IMAGE"
fi

section "nginx -t, hash CSP trong image"
if dk run --rm --add-host backend:127.0.0.1 "$IMAGE" nginx -t > "$TMP/nginx-t.log" 2>&1; then
  pass "nginx -t"
else
  fail "nginx -t: $(cat "$TMP/nginx-t.log")"
fi
# So hash của script inline trong dist/index.html (đúng file trình duyệt nhận) với CSP.
if dk run --rm "$IMAGE" sh -c 'cat /usr/share/nginx/html/index.html; printf "\n@@CONF@@\n"; cat /etc/nginx/snippets/page-headers.conf' \
  | node -e '
    const crypto = require("node:crypto");
    let data = "";
    process.stdin.on("data", (c) => (data += c)).on("end", () => {
      const [html, conf] = data.split("\n@@CONF@@\n");
      const want = [...html.matchAll(/<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
        .filter((m) => !/\ssrc\s*=/i.test(m[1] ?? ""))
        .map((m) => `sha256-${crypto.createHash("sha256").update(m[2], "utf8").digest("base64")}`);
      const missing = want.filter((h) => !conf.includes(`'"'"'${h}'"'"'`));
      if (want.length === 0 || missing.length) { console.error("thiếu", missing, "trong", want); process.exit(1); }
    });'; then
  pass "hash script inline của dist/index.html có trong CSP"
else
  fail "hash script inline của dist/index.html không khớp CSP"
fi

section "Khởi động mock backend + nginx"
dk network create "$NET" >/dev/null
dk run -d --name "$MOCK" --network "$NET" --network-alias backend python:3.11-alpine \
  python -u -c "$(cat "$SCRIPT_DIR/mock_backend.py")" >/dev/null
dk run -d --name "$WEB" --network "$NET" -p "127.0.0.1:$PORT:80" "$IMAGE" >/dev/null
ready=0
for _ in $(seq 1 30); do
  if curl -sf -o /dev/null "$BASE/" && curl -sf -o /dev/null "$BASE/api/health"; then ready=1; break; fi
  sleep 1
done
if [ "$ready" = 1 ]; then pass "nginx và mock sẵn sàng tại $BASE"; else fail "nginx/mock không sẵn sàng"; exit 1; fi
if dk exec "$WEB" wget -qO- http://127.0.0.1/ >/dev/null; then
  pass "lệnh HEALTHCHECK của image (wget http://127.0.0.1/)"
else
  fail "lệnh HEALTHCHECK của image"
fi

JS="$(curl -s "$BASE/" | grep -oE '/assets/[^"]+\.js' | head -n 1)"
CSS="$(curl -s "$BASE/" | grep -oE '/assets/[^"]+\.css' | head -n 1)"
[ -n "$JS" ] && [ -n "$CSS" ] || { fail "không tìm thấy asset JS/CSS trong index.html"; exit 1; }

# Các bước chờ dài chạy nền song song với phần còn lại (AC-02).
if [ "$QUICK" = 0 ]; then
  STREAM_GAP=150
  curl -s -o /dev/null -w '%{http_code} %{time_total}' -X POST "$BASE/api/ingest/chunk?sleep=200" > "$TMP/chunk.out" &
  CHUNK_PID=$!
  curl -s -o /dev/null -w '%{http_code} %{time_total}' "$BASE/api/slow?sleep=130" > "$TMP/slow.out" &
  SLOW_PID=$!
else
  STREAM_GAP=5
fi

section "Trần body (AC-01)"
head -c $((30 * 1024 * 1024)) /dev/zero | curl -s -o "$TMP/upload.json" -D - -X POST \
  -H 'Content-Type: application/octet-stream' --data-binary @- "$BASE/api/documents" | tr -d '\r' > "$TMP/upload.h"
expect_status "$TMP/upload.h" 202 "POST /api/documents 30MB"
if grep -q "\"received\": $((30 * 1024 * 1024))" "$TMP/upload.json"; then pass "backend nhận đủ 30MB"; else fail "backend nhận: $(cat "$TMP/upload.json")"; fi

head -c $((56 * 1024 * 1024)) /dev/zero | fetch "$TMP/upload-413.h" -X POST \
  -H 'Content-Type: application/octet-stream' --data-binary @- "$BASE/api/documents"
expect_status "$TMP/upload-413.h" 413 "POST /api/documents 56MB"

head -c $((5 * 1024 * 1024)) /dev/zero | curl -s -o "$TMP/markdown.json" -D - -X PUT \
  -H 'Content-Type: application/json' --data-binary @- "$BASE/api/documents/x/markdown" | tr -d '\r' > "$TMP/markdown.h"
expect_status "$TMP/markdown.h" 200 "PUT /api/documents/x/markdown 5MB"
if grep -q "\"received\": $((5 * 1024 * 1024))" "$TMP/markdown.json"; then pass "backend nhận đủ 5MB"; else fail "backend nhận: $(cat "$TMP/markdown.json")"; fi

head -c $((10 * 1024)) /dev/zero | fetch "$TMP/chat-ok.h" -X POST --data-binary @- "$BASE/api/chat"
expect_status "$TMP/chat-ok.h" 200 "POST /api/chat 10KB"
head -c $((70 * 1024)) /dev/zero | fetch "$TMP/chat-413.h" -X POST --data-binary @- "$BASE/api/chat"
expect_status "$TMP/chat-413.h" 413 "POST /api/chat 70KB"
head -c $((70 * 1024)) /dev/zero | fetch "$TMP/stream-413.h" -X POST --data-binary @- "$BASE/api/chat/stream"
expect_status "$TMP/stream-413.h" 413 "POST /api/chat/stream 70KB"
head -c $((2 * 1024 * 1024)) /dev/zero | fetch "$TMP/page-413.h" -X POST --data-binary @- "$BASE/"
expect_status "$TMP/page-413.h" 413 "POST / 2MB"

section "Security header (AC-03)"
fetch "$TMP/root.h" "$BASE/"
expect_status "$TMP/root.h" 200 "GET /"
expect_security_headers "$TMP/root.h" page "GET /"
fetch "$TMP/js.h" "$BASE$JS"
expect_security_headers "$TMP/js.h" page "GET $JS"
fetch "$TMP/fallback.h" "$BASE/chat"
expect_status "$TMP/fallback.h" 200 "GET /chat (SPA fallback)"
expect_security_headers "$TMP/fallback.h" page "GET /chat"
fetch "$TMP/asset-404.h" "$BASE/assets/khong-co.js"
expect_status "$TMP/asset-404.h" 404 "GET /assets/khong-co.js"
expect_security_headers "$TMP/asset-404.h" page "404 asset"
expect_security_headers "$TMP/page-413.h" page "413 trang"
fetch "$TMP/health.h" "$BASE/api/health"
expect_status "$TMP/health.h" 200 "GET /api/health"
expect_security_headers "$TMP/health.h" api "GET /api/health"
fetch "$TMP/api-404.h" "$BASE/api/khong-co"
expect_status "$TMP/api-404.h" 404 "GET /api/khong-co"
expect_security_headers "$TMP/api-404.h" api "404 /api"
expect_security_headers "$TMP/upload-413.h" api "413 upload"
expect_security_headers "$TMP/chat-413.h" api "413 chat"

section "gzip, cache (AC-05)"
for target in "$JS" "$CSS" /api/json; do
  fetch "$TMP/gz.h" -H 'Accept-Encoding: gzip' "$BASE$target"
  expect_header "$TMP/gz.h" Content-Encoding gzip "GET $target (Accept-Encoding: gzip)"
  expect_header "$TMP/gz.h" Vary "Accept-Encoding" "GET $target"
done
fetch "$TMP/plain.h" "$BASE$JS"
expect_no_header "$TMP/plain.h" Content-Encoding "GET $JS (không Accept-Encoding)"
expect_header "$TMP/js.h" Cache-Control "public, max-age=31536000, immutable" "GET $JS"
expect_header "$TMP/js.h" Content-Type "application/javascript|text/javascript" "GET $JS"
expect_no_header "$TMP/asset-404.h" Cache-Control "404 asset"
for target in / /index.html /chat; do
  fetch "$TMP/page.h" "$BASE$target"
  expect_header "$TMP/page.h" Cache-Control "no-cache" "GET $target"
  expect_header "$TMP/page.h" Content-Type "text/html" "GET $target"
done

section "Stream NDJSON và timeout (AC-02)"
start="$(date +%s)"
curl -sN -X POST -H 'Content-Type: application/json' -H 'Accept-Encoding: gzip' -d '{}' \
  -D "$TMP/stream.raw" "$BASE/api/chat/stream?gap=$STREAM_GAP" \
  | while IFS= read -r line; do echo "$(($(date +%s) - start)) $line"; done > "$TMP/stream.log"
tr -d '\r' < "$TMP/stream.raw" > "$TMP/stream.h"
expect_status "$TMP/stream.h" 200 "POST /api/chat/stream (khoảng lặng ${STREAM_GAP}s)"
expect_no_header "$TMP/stream.h" Content-Encoding "stream"
expect_security_headers "$TMP/stream.h" api "stream"
first="$(sed -n '1p' "$TMP/stream.log")"
second="$(sed -n '2p' "$TMP/stream.log")"
if [ "${first%% *}" -le 2 ] 2>/dev/null && [ "${first#* }" = '{"type":"start"}' ]; then
  pass "dòng 1 tới ngay (${first%% *}s), không chờ cả response"
else
  fail "dòng 1: '$first'"
fi
if [ "${second%% *}" -ge $((STREAM_GAP - 2)) ] 2>/dev/null && [ "${second#* }" = '{"type":"done"}' ]; then
  pass "dòng 2 tới sau khoảng lặng (${second%% *}s)"
else
  fail "dòng 2: '$second'"
fi

if [ "$QUICK" = 0 ]; then
  wait "$CHUNK_PID" "$SLOW_PID"
  read -r code secs < "$TMP/chunk.out"
  if [ "$code" = 200 ]; then pass "POST /api/ingest/chunk chạy ${secs}s -> 200"; else fail "POST /api/ingest/chunk: $code sau ${secs}s"; fi
  read -r code secs < "$TMP/slow.out"
  if [ "$code" = 504 ] && [ "${secs%%.*}" -ge 115 ] && [ "${secs%%.*}" -le 130 ]; then
    pass "GET /api/slow (130s) bị cắt -> 504 sau ${secs}s"
  else
    fail "GET /api/slow: $code sau ${secs}s (cần 504 ở ~120s)"
  fi
else
  skip "timeout chia đoạn 200s và /api/ 120s (--quick)"
fi

echo
echo "Kết quả: $PASS pass, $FAIL fail, $SKIP skip"
[ "$FAIL" = 0 ]
