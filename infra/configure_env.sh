#!/usr/bin/env bash
# infra/configure_env.sh — Write the .env file with production secrets.
# SECURITY NOTE: This script writes secrets to disk with chmod 600.
# In real production, use AWS Secrets Manager + aws secretsmanager get-secret-value
# and inject into systemd via EnvironmentFile or directly in ExecStart.
# Never commit the actual .env file to version control.

set -e  # Exit immediately on any error

APP_DIR="${APP_DIR:-/opt/text-to-sql}"  # Default app directory (overridable)
ENV_FILE="$APP_DIR/.env"

echo "=== Writing .env to $ENV_FILE ==="

# Prompt operator for secrets if not pre-set in environment
OPENAI_API_KEY="${OPENAI_API_KEY:?ERROR: OPENAI_API_KEY must be set before running this script}"
OPENAI_MODEL="${OPENAI_MODEL:-gpt-4o}"
DATABASE_URL="${DATABASE_URL:-sqlite:///./data/olist.db}"
CHROMA_PERSIST_DIR="${CHROMA_PERSIST_DIR:-$APP_DIR/chroma_store}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-text-embedding-3-small}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

cat > "$ENV_FILE" <<'COMMENTS'
# OpenAI configuration
# OPENAI_API_KEY: Secret key from https://platform.openai.com/api-keys
COMMENTS
printf 'OPENAI_API_KEY=%q\n' "$OPENAI_API_KEY"    >> "$ENV_FILE"
printf '\n# OPENAI_MODEL: Which GPT model to use. gpt-4o is recommended for SQL accuracy.\n' >> "$ENV_FILE"
printf 'OPENAI_MODEL=%q\n' "$OPENAI_MODEL"         >> "$ENV_FILE"
printf '\n# Database connection string.\n# SQLite for dev/staging; set to postgresql://user:pass@host/db for production.\n' >> "$ENV_FILE"
printf 'DATABASE_URL=%q\n' "$DATABASE_URL"          >> "$ENV_FILE"
printf '\n# ChromaDB vector store persistence directory.\n# Must be an absolute path in production so gunicorn workers can find it.\n' >> "$ENV_FILE"
printf 'CHROMA_PERSIST_DIR=%q\n' "$CHROMA_PERSIST_DIR" >> "$ENV_FILE"
printf '\n# OpenAI embedding model. text-embedding-3-small is cheap and accurate enough.\n' >> "$ENV_FILE"
printf 'EMBEDDING_MODEL=%q\n' "$EMBEDDING_MODEL"    >> "$ENV_FILE"
printf '\n# Python logging level. Use INFO in production, DEBUG only for troubleshooting.\n' >> "$ENV_FILE"
printf 'LOG_LEVEL=%q\n' "$LOG_LEVEL"                >> "$ENV_FILE"

chmod 600 "$ENV_FILE"   # Only owner (ubuntu) can read — prevents other users from seeing the key
echo "✅ .env written to $ENV_FILE with permissions 600."
echo "⚠  In production, consider using AWS Secrets Manager instead of a file."
