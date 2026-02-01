#!/bin/bash
set -euo pipefail

# ------------------------------------------------------------
# Make Homebrew Postgres tools visible even inside IDE shells
# ------------------------------------------------------------
export PATH="/opt/homebrew/opt/postgresql@16/bin:/opt/homebrew/bin:$PATH"

# ------------------------------------------------------------
# Remote (SSH) config
# ------------------------------------------------------------
SSH_HOST="skh"
SSH_OPTS=(-o ClearAllForwardings=yes)

REMOTE_BACKUP_DIR="/home/skh/backup"
REMOTE_BACKUP_SCRIPT="/home/skh/tasks/backup_db.sh"
RUN_REMOTE_BACKUP="true"   # "true" or "false"

# Where to store pulled dumps on your Mac
LOCAL_DUMP_DIR="$HOME/skh_db_dumps"
mkdir -p "$LOCAL_DUMP_DIR"

# ------------------------------------------------------------
# Local Postgres target
# ------------------------------------------------------------
LOCAL_PGHOST="127.0.0.1"
LOCAL_PGPORT="5435"
LOCAL_PGUSER="skh_user"
LOCAL_PGPASSWORD="skh_password"
LOCAL_DBNAME="skh"

DO_DROP_CREATE="true"      # "true" or "false"

# ------------------------------------------------------------
# Resolve psql robustly
# ------------------------------------------------------------
PSQL_BIN="$(command -v psql || true)"
if [[ -z "$PSQL_BIN" ]] && [[ -x "/opt/homebrew/opt/postgresql@16/bin/psql" ]]; then
  PSQL_BIN="/opt/homebrew/opt/postgresql@16/bin/psql"
fi
if [[ -z "$PSQL_BIN" ]]; then
  echo "ERROR: psql not found."
  exit 1
fi

echo "==> Using psql: $PSQL_BIN"
echo "==> Using SSH host: $SSH_HOST (forwardings disabled for script calls)"

# ------------------------------------------------------------
# Sanity: local connection check
# ------------------------------------------------------------
export PGPASSWORD="$LOCAL_PGPASSWORD"
if ! "$PSQL_BIN" -h "$LOCAL_PGHOST" -p "$LOCAL_PGPORT" -U "$LOCAL_PGUSER" -d postgres -P pager=off -c "select 1;" >/dev/null 2>&1; then
  echo "ERROR: Cannot connect to local Postgres at $LOCAL_PGHOST:$LOCAL_PGPORT as $LOCAL_PGUSER."
  unset PGPASSWORD
  exit 1
fi
unset PGPASSWORD

# ------------------------------------------------------------
# 1) Optionally run remote backup script
# ------------------------------------------------------------
if [[ "$RUN_REMOTE_BACKUP" == "true" ]]; then
  echo "==> Running remote backup script on server..."
  ssh "${SSH_OPTS[@]}" "$SSH_HOST" "bash '$REMOTE_BACKUP_SCRIPT'"
fi

# ------------------------------------------------------------
# 2) Find newest .sql on remote
# ------------------------------------------------------------
LATEST_REMOTE_SQL="$(
  ssh "${SSH_OPTS[@]}" "$SSH_HOST" \
    "ls -t '$REMOTE_BACKUP_DIR'/*.sql 2>/dev/null | head -n 1"
)"
if [[ -z "${LATEST_REMOTE_SQL:-}" ]]; then
  echo "ERROR: No .sql backups found in $REMOTE_BACKUP_DIR on remote."
  exit 1
fi

BASENAME="$(basename "$LATEST_REMOTE_SQL")"
LOCAL_SQL_PATH="$LOCAL_DUMP_DIR/$BASENAME"

echo "==> Latest remote dump: $LATEST_REMOTE_SQL"
echo "==> Downloading to: $LOCAL_SQL_PATH"

# ------------------------------------------------------------
# 3) Download newest dump
# ------------------------------------------------------------
scp -o ClearAllForwardings=yes "$SSH_HOST:$LATEST_REMOTE_SQL" "$LOCAL_SQL_PATH"

# ------------------------------------------------------------
# 4) Recreate local DB (optional)
# ------------------------------------------------------------
if [[ "$DO_DROP_CREATE" == "true" ]]; then
  echo "==> Recreating local database '$LOCAL_DBNAME' on $LOCAL_PGHOST:$LOCAL_PGPORT..."
  export PGPASSWORD="$LOCAL_PGPASSWORD"

  "$PSQL_BIN" -h "$LOCAL_PGHOST" -p "$LOCAL_PGPORT" -U "$LOCAL_PGUSER" -d postgres -v ON_ERROR_STOP=1 -P pager=off <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${LOCAL_DBNAME}'
  AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS "${LOCAL_DBNAME}";
CREATE DATABASE "${LOCAL_DBNAME}";
SQL

  unset PGPASSWORD
else
  echo "==> DO_DROP_CREATE=false, will restore into existing DB '$LOCAL_DBNAME' (must exist)."
fi

# ------------------------------------------------------------
# 5) Print restore-target server version
# ------------------------------------------------------------
echo "==> Restore-target server version:"
export PGPASSWORD="$LOCAL_PGPASSWORD"
"$PSQL_BIN" -h "$LOCAL_PGHOST" -p "$LOCAL_PGPORT" -U "$LOCAL_PGUSER" -d "$LOCAL_DBNAME" -P pager=off -v ON_ERROR_STOP=1 -c "select version();"
unset PGPASSWORD

# ------------------------------------------------------------
# 6) Sanitize dump for local restore
#    Keep ONLY what you actually need.
#    Remote dump now uses --no-owner --no-privileges, so OWNER/GRANT stripping is unnecessary.
# ------------------------------------------------------------
SANITIZED_SQL_PATH="${LOCAL_SQL_PATH%.sql}.sanitized.sql"

# Remove only the non-standard transaction_timeout line (if present)
sed -E \
  -e '/^[[:space:]]*SET[[:space:]]+transaction_timeout[[:space:]]*=.*;[[:space:]]*$/Id' \
  "$LOCAL_SQL_PATH" > "$SANITIZED_SQL_PATH"

if grep -qi 'transaction_timeout' "$LOCAL_SQL_PATH"; then
  echo "==> Note: sanitized dump (removed SET transaction_timeout)."
fi


# ------------------------------------------------------------
# 7) Restore sanitized dump (single transaction + log output)
#    This prevents "schema-only" partial restores if COPY fails mid-way.
# ------------------------------------------------------------
RESTORE_LOG="${LOCAL_SQL_PATH%.sql}.restore.log"

echo "==> Restoring sanitized dump into '$LOCAL_DBNAME'..."
echo "==> Logging restore output to: $RESTORE_LOG"

export PGPASSWORD="$LOCAL_PGPASSWORD"
"$PSQL_BIN" -h "$LOCAL_PGHOST" -p "$LOCAL_PGPORT" -U "$LOCAL_PGUSER" -d "$LOCAL_DBNAME" \
  -v ON_ERROR_STOP=1 -P pager=off --single-transaction \
  < "$SANITIZED_SQL_PATH" | tee "$RESTORE_LOG"
unset PGPASSWORD

# ------------------------------------------------------------
# 8) Quick sanity checks: confirm data loaded
# ------------------------------------------------------------
echo "==> Quick sanity counts:"
export PGPASSWORD="$LOCAL_PGPASSWORD"
"$PSQL_BIN" -h "$LOCAL_PGHOST" -p "$LOCAL_PGPORT" -U "$LOCAL_PGUSER" -d "$LOCAL_DBNAME" -P pager=off -v ON_ERROR_STOP=1 \
  -c "select count(*) as students from public.students;"
"$PSQL_BIN" -h "$LOCAL_PGHOST" -p "$LOCAL_PGPORT" -U "$LOCAL_PGUSER" -d "$LOCAL_DBNAME" -P pager=off -v ON_ERROR_STOP=1 \
  -c "select count(*) as users from public.users;"
unset PGPASSWORD

echo "==> Done. Restored local DB '$LOCAL_DBNAME' from $BASENAME"
echo "==> Dump saved at: $LOCAL_SQL_PATH"
echo "==> Sanitized dump saved at: $SANITIZED_SQL_PATH"
echo "==> Restore log saved at: $RESTORE_LOG"
