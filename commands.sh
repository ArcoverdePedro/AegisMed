#!/bin/sh
set -eu

# `docker compose run aegis_share <comando>` deve executar o comando solicitado
# sem iniciar o servidor/migrations automaticamente.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

PORT="${PORT:-8000}"
# Migrations apagam dados em algumas versoes: em producao rodam como passo explicito,
# depois do backup (README). RUN_MIGRATIONS=true so para desenvolvimento/CI.
RUN_MIGRATIONS="${RUN_MIGRATIONS:-false}"
COLLECT_STATIC="${COLLECT_STATIC:-true}"
WEB_WORKERS="${WEB_WORKERS:-1}"

if [ -z "${REDIS_URL:-}" ] && [ "$WEB_WORKERS" != "1" ]; then
  echo "REDIS_URL nao configurada; WEB_WORKERS foi reduzido para 1 para manter WebSockets consistentes."
  WEB_WORKERS=1
fi

echo "Aguardando banco de dados..."
attempt=1
max_attempts="${DB_STARTUP_ATTEMPTS:-30}"

until python - <<'PY'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
import django
django.setup()
from django.db import connection
connection.ensure_connection()
connection.close()
PY
do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Banco de dados indisponivel apos ${max_attempts} tentativas."
    exit 1
  fi
  attempt=$((attempt + 1))
  sleep 2
done

if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Aplicando migrations..."
  python manage.py migrate --noinput
elif ! python manage.py migrate --check >/dev/null; then
  echo "Ha migrations pendentes. Faca o backup e rode:"
  echo "  docker compose run --rm aegis_share python manage.py migrate"
  exit 1
fi

if [ "$COLLECT_STATIC" = "true" ]; then
  echo "Coletando arquivos estaticos..."
  python manage.py collectstatic --noinput
fi

echo "Iniciando AegisShare na porta ${PORT} com ${WEB_WORKERS} worker(s)..."
exec granian mysite.asgi:application \
  --host 0.0.0.0 \
  --port "$PORT" \
  --interface asgi \
  --workers "$WEB_WORKERS"
