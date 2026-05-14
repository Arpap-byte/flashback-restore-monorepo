#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Vérification post-déploiement Flashback Restore
# Vérifie que tous les services sont opérationnels et les données intactes.
#
# Usage: bash scripts/post_deploy_check.sh
# ---------------------------------------------------------------------------
set -euo pipefail

PASS=0
FAIL=0
SITE_URL="${SITE_URL:-https://flashback-restore.com}"
API_URL="${API_URL:-http://localhost:8000}"

log_pass() { echo "   ✅ $1"; PASS=$((PASS + 1)); }
log_fail() { echo "   ❌ $1"; FAIL=$((FAIL + 1)); }

echo "🔍 Vérification post-déploiement — $(date)"

# --- Services ---
echo ""
echo "--- Services ---"
for svc in flashback-backend flashback-arq-worker redis-server; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        log_pass "$svc actif"
    else
        log_fail "$svc INACTIF"
    fi
done

# --- API ---
echo ""
echo "--- API ---"
if curl -sf "${API_URL}/api/health" > /dev/null 2>&1; then
    log_pass "API /health OK"
else
    log_fail "API /health ÉCHEC"
fi

# --- Base de données ---
echo ""
echo "--- Base de données ---"
DB_PATH="${DB_PATH:-/opt/flashback-restore-monorepo/backend/flashback.db}"
if [ -f "$DB_PATH" ]; then
    if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        log_pass "DB integrity_check OK"
    else
        log_fail "DB CORROMPUE"
    fi

    NB_USERS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM utilisateurs;" 2>/dev/null || echo "?")
    NB_TRAVAUX=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM travaux;" 2>/dev/null || echo "?")
    echo "      👥 Utilisateurs: $NB_USERS | 📷 Travaux: $NB_TRAVAUX"

    # Vérification utilisateur témoin (APEX-CYBER)
    APEX_CREDITS=$(sqlite3 "$DB_PATH" "SELECT credits FROM utilisateurs WHERE email='apexcyber.eu@gmail.com';" 2>/dev/null || echo "ABSENT")
    if [ "$APEX_CREDITS" = "ABSENT" ]; then
        log_fail "APEX-CYBER ABSENT de la DB"
    elif [ "$APEX_CREDITS" -ge 0 ] 2>/dev/null; then
        echo "      🧪 APEX-CYBER: $APEX_CREDITS crédits"
        log_pass "APEX-CYBER présent ($APEX_CREDITS crédits)"
    else
        log_fail "APEX-CYBER crédits incohérents: $APEX_CREDITS"
    fi
else
    log_fail "DB introuvable: $DB_PATH"
fi

# --- WAL ---
echo ""
echo "--- WAL ---"
WAL_SIZE=$(stat -c%s "${DB_PATH}-wal" 2>/dev/null || echo "0")
if [ "$WAL_SIZE" -gt 10485760 ]; then  # > 10MB
    log_fail "WAL trop volumineux: $((WAL_SIZE / 1024 / 1024))MB — checkpoint forcé"
    sqlite3 "$DB_PATH" "PRAGMA wal_checkpoint(TRUNCATE);"
else
    log_pass "WAL: $((WAL_SIZE / 1024))KB"
fi

# --- Résumé ---
echo ""
echo "--- Résumé ---"
echo "   ✅ $PASS succès"
if [ "$FAIL" -gt 0 ]; then
    echo "   ❌ $FAIL échecs"
    exit 1
else
    echo "   🎉 Tout est OK !"
fi
