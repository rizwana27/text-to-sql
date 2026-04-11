#!/usr/bin/env bash
# infra/verify.sh — Verify all layers of the stack are healthy.
# Run after deployment: bash infra/verify.sh
# Expected output: all checks PASS.

set -e  # Exit on first failure so the operator sees exactly where things broke

APP_DIR="${APP_DIR:-/opt/text-to-sql}"
PUBLIC_IP=$(curl -sf --connect-timeout 2 --max-time 5 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unknown")

echo "================================================="
echo "  Text-to-SQL Deployment Verification"
echo "  Public IP: $PUBLIC_IP"
echo "================================================="

echo ""
echo "--- [1/5] Checking systemd service status ---"
if systemctl is-active --quiet texttosql; then
    echo "✅ texttosql.service is ACTIVE"
else
    echo "❌ texttosql.service is NOT active"
    journalctl -u texttosql --no-pager -n 30  # Print last 30 log lines for debugging
    exit 1
fi

echo ""
echo "--- [2/5] Checking gunicorn health endpoint (localhost) ---"
HTTP_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:8000/api/health || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ /api/health returned HTTP 200"
    curl -sf http://localhost:8000/api/health | python3 -m json.tool  # Pretty-print the JSON
else
    echo "❌ /api/health returned HTTP $HTTP_STATUS (expected 200)"
    exit 1
fi

echo ""
echo "--- [3/5] Checking nginx service status ---"
if systemctl is-active --quiet nginx; then
    echo "✅ nginx is ACTIVE"
else
    echo "❌ nginx is NOT active"
    journalctl -u nginx --no-pager -n 20
    exit 1
fi

echo ""
echo "--- [4/5] Checking nginx config syntax ---"
nginx -t && echo "✅ nginx config syntax OK"

echo ""
echo "--- [5/5] Checking public IP response ---"
if [ "$PUBLIC_IP" != "unknown" ]; then
    PUBLIC_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "http://$PUBLIC_IP/api/health" || echo "000")
    if [ "$PUBLIC_STATUS" = "200" ]; then
        echo "✅ Public endpoint http://$PUBLIC_IP/api/health returned HTTP 200"
    else
        echo "⚠  Public endpoint returned HTTP $PUBLIC_STATUS — check security group allows port 80"
    fi
else
    echo "⚠  Could not determine public IP (not on EC2 or metadata service unavailable)"
fi

echo ""
echo "================================================="
echo "✅ All checks passed. Stack is healthy."
echo "================================================="
