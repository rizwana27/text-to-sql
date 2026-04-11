# Troubleshooting Guide

Quick reference for the most common deployment issues.

---

## 502 Bad Gateway

**Symptom:** nginx returns `502 Bad Gateway` for `/api/*` requests.

**Causes & fixes:**
1. **gunicorn not running:**
   ```bash
   sudo systemctl status texttosql
   sudo journalctl -u texttosql -n 50 --no-pager
   sudo systemctl restart texttosql
   ```
2. **Wrong bind address in service file:** Confirm `--bind 127.0.0.1:8000` in `texttosql.service`.
3. **Port 8000 not listening:**
   ```bash
   ss -tlnp | grep 8000
   ```
4. **nginx upstream misconfigured:** Verify `proxy_pass http://127.0.0.1:8000;` in nginx.conf.
5. **Worker timeout on slow LLM call:** Increase `--timeout` in ExecStart and `proxy_read_timeout` in nginx.conf.

---

## SSH Connection Refused

**Symptom:** `ssh: connect to host X.X.X.X port 22: Connection refused`

**Causes & fixes:**
1. **EC2 security group blocks port 22:** Add inbound rule for TCP/22 from your IP.
2. **Instance still booting:** Wait 2 minutes after launch, then retry.
3. **Wrong key pair:** Ensure you're using `~/.ssh/your-key.pem` and the key matches the instance.
4. **Instance stopped:** Check EC2 console → Instance State → Start.
   ```bash
   ssh -i ~/.ssh/your-key.pem ubuntu@<public-ip>
   ```

---

## ChromaDB Collection Not Found

**Symptom:** `ValueError: Collection 'schema_index' does not exist.` in gunicorn logs.

**Causes & fixes:**
1. **build_index.py was never run:**
   ```bash
   cd /opt/text-to-sql
   source venv/bin/activate && source .env
   python -m agent.build_index
   sudo systemctl restart texttosql
   ```
2. **Wrong CHROMA_PERSIST_DIR:** The path in `.env` must match where `build_index.py` wrote files. Use absolute paths.
3. **Permission issue:** Ensure `ubuntu` user owns `chroma_store/`:
   ```bash
   chown -R ubuntu:ubuntu /opt/text-to-sql/chroma_store
   ```

---

## OpenAI 401 Unauthorized

**Symptom:** `openai.AuthenticationError: 401 Unauthorized` in logs.

**Causes & fixes:**
1. **OPENAI_API_KEY not set or wrong:** Check `.env` file:
   ```bash
   grep OPENAI_API_KEY /opt/text-to-sql/.env
   ```
2. **Key has been revoked:** Generate a new key at https://platform.openai.com/api-keys.
3. **EnvironmentFile not loaded:** Confirm `EnvironmentFile=/opt/text-to-sql/.env` in the service file and restart.

---

## OpenAI 429 Rate Limited / Quota Exceeded

**Symptom:** `openai.RateLimitError: 429 Too Many Requests`

**Causes & fixes:**
1. **Hit requests-per-minute limit:** Implement exponential backoff. LangChain does this automatically with `max_retries`.
2. **Exceeded monthly quota:** Check usage at https://platform.openai.com/usage and upgrade plan.
3. **Too many concurrent workers:** Reduce gunicorn `--workers` to 2 to lower parallel OpenAI calls.

---

## Gunicorn Worker Timeout

**Symptom:** `[CRITICAL] WORKER TIMEOUT` in gunicorn logs; client gets 502.

**Causes & fixes:**
1. **LLM call taking too long:** GPT-4o with a long prompt can take 30-60s. Increase timeouts:
   - `texttosql.service`: change `--timeout 120` to `--timeout 180`
   - `nginx.conf`: change `proxy_read_timeout 120s` to `proxy_read_timeout 180s`
2. **ChromaDB slow cold start:** First request after deploy is slow. Use a readiness check.
3. **DB query on large dataset:** Add `LIMIT 1000` to generated SQL (already enforced in the prompt).

---

## Blank React Page (White Screen)

**Symptom:** Browser shows blank page; no errors in nginx logs.

**Causes & fixes:**
1. **Frontend not built:** Run `npm run build` in the `frontend/` directory.
2. **nginx root path wrong:** Confirm `root /opt/text-to-sql/frontend/dist;` in nginx.conf.
3. **SPA routing not configured:** Ensure `try_files $uri $uri/ /index.html;` is in nginx location block.
4. **JavaScript error in browser console:** Open DevTools → Console tab to see the actual error.
5. **Old dist/ cached:** Hard reload with `Ctrl+Shift+R` or `Cmd+Shift+R`.
   ```bash
   # Rebuild frontend
   cd /opt/text-to-sql/frontend && npm run build
   sudo systemctl reload nginx
   ```
