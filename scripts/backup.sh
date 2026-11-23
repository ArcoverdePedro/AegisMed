#!/usr/bin/env bash
# Backup cifrado do banco da stack Compose. Uso: scripts/backup.sh <diretorio-destino>
# BACKUP_KEEP_DAYS (padrao 30): apaga do destino so lotes db-*.aegisbak/SHA256SUMS-* mais antigos,
# e so depois que o lote novo foi conferido. 0 desativa a limpeza.
# Exige BACKUP_ENCRYPTION_KEY no .env. FILE_ENCRYPTION_KEY e BACKUP_ENCRYPTION_KEY NAO entram no
# backup: guarde-as em cofre separado, senao a restauracao nao decifra nada.
set -euo pipefail

dest="${1:?informe o diretorio de destino}"
compose=(docker compose ${COMPOSE_FILE_ARGS:-})
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
umask 077
mkdir -p "$dest"

"${compose[@]}" exec -T postgres sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | "${compose[@]}" exec -T aegis_share python manage.py backup_seal \
  > "$dest/db-$stamp.dump.aegisbak.partial"

# Confere autenticacao completa antes de considerar o backup valido.
for part in "$dest"/*-"$stamp".*.partial; do
  "${compose[@]}" exec -T aegis_share python manage.py backup_open < "$part" > /dev/null
  mv "$part" "${part%.partial}"
done
sha256sum "$dest"/*-"$stamp".*.aegisbak > "$dest/SHA256SUMS-$stamp"
keep_days="${BACKUP_KEEP_DAYS:-30}"
if [ "$keep_days" -gt 0 ]; then
  find "$dest" -maxdepth 1 -type f \( -name 'db-*.dump.aegisbak' -o -name 'SHA256SUMS-*' \) \
    -mtime +"$keep_days" -print -delete
fi
echo "backup ok: $dest ($stamp)"
