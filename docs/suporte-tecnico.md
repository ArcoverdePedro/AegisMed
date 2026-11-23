# Guia de suporte técnico — AegisShare

Para a equipe de TI que instala, atualiza e mantém o sistema. O uso de cada módulo está no [Manual do usuário](manual-do-usuario.md). Detalhes de configuração ficam no [README](../README.md) e as mudanças de cada versão no [CHANGELOG](../CHANGELOG.md).

## Sumário

1. [Arquitetura](#1-arquitetura)
2. [Instalação](#2-instalação)
3. [Atualização de versão](#3-atualização-de-versão)
4. [Backup e restauração](#4-backup-e-restauração)
5. [Rotina e comandos úteis](#5-rotina-e-comandos-úteis)
6. [Usuários, perfis e acesso](#6-usuários-perfis-e-acesso)
7. [Monitoramento](#7-monitoramento)
8. [Solução de problemas](#8-solução-de-problemas)
9. [Segurança e chaves](#9-segurança-e-chaves)
10. [Como pedir ajuda](#10-como-pedir-ajuda)

---

## 1. Arquitetura

```text
Estações (navegador) ──HTTPS──> caddy (perfil "proxy", portas 80/443)
                                   │
                                   ▼
                            aegis_share (Django + Granian, porta 8000 só em 127.0.0.1)
                              │                 │
                              ▼                 ▼
                         postgres            redis
                    (volume postgres_data) (volume redis_data)
```

| Serviço | Função | Dados persistentes |
|---|---|---|
| `aegis_share` | aplicação web (usuário `aegis`, sem root) | nenhum: tudo no banco |
| `postgres` | banco PostgreSQL 18, fonte de verdade | volume `postgres_data` |
| `redis` | cache, limite de tentativas de login e tempo real (mapa de leitos) | volume `redis_data` (descartável) |
| `caddy` | HTTPS e certificados | volumes `caddy_data` (inclui a CA interna) e `caddy_config` |

**O que precisa de backup:** o banco (via `scripts/backup.sh`), o arquivo `.env` e as chaves (seção 9). O Redis pode ser perdido sem prejuízo.

**Ponto de partida para o servidor** (a validar com o volume real): 2 vCPU, 4 GB de RAM e 40 GB de disco, mais o espaço dos backups. Linux com Docker Engine e o plugin Compose.

## 2. Instalação

```bash
git clone https://github.com/ArcoverdePedro/AegisShare.git /opt/aegisshare
cd /opt/aegisshare
cp .env-example .env
python3 scripts/generate_secrets.py --install-env .env
```

Edite o `.env` e ajuste pelo menos:

```env
POSTGRES_PASSWORD=<senha forte>
DOMAIN=his.seuhospital.gov.br
ALLOWED_HOSTS=his.seuhospital.gov.br
CSRF_TRUSTED_ORIGINS=https://his.seuhospital.gov.br
CADDY_TLS=internal              # nome só da rede interna; use acme se o domínio for público
TRUSTED_PROXY_IPS=172.16.0.0/12 # rede Docker, para a auditoria registrar o IP real
BACKUP_ENCRYPTION_KEY=<gere com o comando da seção 4>
TIME_ZONE=America/Fortaleza     # ajuste ao fuso do hospital
```

Suba a stack:

```bash
docker compose build
docker compose run --rm aegis_share python manage.py migrate
docker compose --profile proxy up -d
docker compose run --rm aegis_share python manage.py sync_role_groups --apply
```

Depois:

1. Acesse `https://DOMINIO/setup/` e crie o **primeiro administrador** (a tela só existe enquanto não houver um).
2. Entre, ative o **2FA** do administrador em **Segurança**.
3. Com `CADDY_TLS=internal`, copie a CA raiz e instale como confiável nas estações (por GPO, por exemplo):
   ```bash
   docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./aegisshare-ca.crt
   ```
4. Configure o DNS interno para que `DOMINIO` aponte para o servidor.
5. Agende o backup (seção 4) e o monitoramento (seção 7).
6. Cadastre os catálogos no Admin: locais/leitos, exames, medicamentos, materiais.

## 3. Atualização de versão

1. Leia as **Notas de atualização** no CHANGELOG: algumas versões apagam tabelas ou exigem passos manuais.
2. Faça backup: `scripts/backup.sh /srv/backups/aegisshare`.
3. Atualize o código e a imagem:
   ```bash
   git pull
   docker compose build
   ```
4. Aplique as migrations: `docker compose run --rm aegis_share python manage.py migrate`
5. Suba: `docker compose --profile proxy up -d`
6. Confira `https://DOMINIO/health/ready/` e faça login.

O container **não inicia** se houver migration pendente. É proposital: código novo nunca roda sobre banco antigo.

**Voltar versão:** volte o código (`git checkout <versão anterior>`), restaure o backup feito no passo 2 (seção 4) e reconstrua a imagem. Não tente desfazer migrations em produção sem antes ensaiar.

## 4. Backup e restauração

Gere a chave de backup uma única vez e guarde **fora do servidor**, separada do backup:

```bash
python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Agende o backup diário (`crontab -e` do usuário que opera o Docker):

```cron
0 2 * * * cd /opt/aegisshare && BACKUP_KEEP_DAYS=30 scripts/backup.sh /srv/backups/aegisshare >> /var/log/aegisshare-backup.log 2>&1
```

O script cifra o `pg_dump`, confere se o arquivo abre e só então apaga os lotes com mais de `BACKUP_KEEP_DAYS` dias. **Copie `/srv/backups/aegisshare` para outro local** (outro prédio, NAS ou nuvem) e confira o log todos os dias.

**Ensaio de restauração (mensal, num servidor de teste):**

```bash
docker compose up -d postgres
docker compose exec -T postgres createdb -U aegisshare restauro
docker compose run --rm -T aegis_share python manage.py backup_open < db-STAMP.dump.aegisbak \
  | docker compose exec -T postgres pg_restore --no-owner -U aegisshare -d restauro
```

Registre a data do ensaio e o tempo gasto. Esse tempo é o seu RTO real.

## 5. Rotina e comandos úteis

| Tarefa | Comando |
|---|---|
| Situação dos serviços | `docker compose ps` |
| Logs da aplicação (JSON) | `docker compose logs -f --tail 200 aegis_share` |
| Saúde | `curl -sk https://DOMINIO/health/ready/` |
| Reiniciar a aplicação | `docker compose restart aegis_share` |
| Shell Django | `docker compose run --rm aegis_share python manage.py shell` |
| Revisão de acessos (CSV) | `docker compose run --rm -T aegis_share python manage.py access_review > acessos.csv` |
| Atualizar tabelas IBGE/etnias/países | `uv run python manage.py update_sus_tables` no repositório de desenvolvimento, depois commit e nova versão |
| Espaço em disco | `df -h` e `docker system df` |

Faça a **revisão de acessos** (`access_review`) periodicamente, por exemplo a cada trimestre: ela lista concessões de pacientes, unidades, permissões e superusuários.

## 6. Usuários, perfis e acesso

- **Criar usuário:** pela tela **Cadastrar usuário** (perfil administrador) ou pelo Admin.
- **Perfis:** no Admin, adicione o usuário aos grupos (Recepção, Médico, Enfermagem, Farmácia, Laboratório, Imagem, Suprimentos, Suprimentos · aprovação, RH, Privacidade). Os grupos são criados por `sync_role_groups --apply` e **são uma proposta**: revise com a direção (gate G02).
- **Acesso a pacientes:** grupos não dão acesso a prontuários. Conceda em **Admin → Pep → Patient access grants** (usuário, paciente, motivo, expiração opcional). Leitos e unidades: **Admin → Adt → User location accesses**.
- **Redefinir senha:**
  ```bash
  docker compose run --rm aegis_share python manage.py changepassword USUARIO
  ```
- **Desativar 2FA de quem perdeu o celular** (confirme a identidade antes):
  ```bash
  docker compose run --rm aegis_share python manage.py shell -c "from aegis_share.models import CustomUser; from aegis_share.services.security import disable_totp; disable_totp(CustomUser.objects.get(username='USUARIO'))"
  ```
- **Bloqueio por tentativas:** após 10 tentativas de login (ou 8 de 2FA) o usuário espera cerca de 5 minutos. Não é preciso intervir.
- **Desligamento:** desative o usuário no Admin (`Active` desmarcado). Não apague: a autoria dos registros clínicos depende dele.
- **Encerrar sessões:** o próprio usuário, em **Segurança**; ou desativando o usuário.

## 7. Monitoramento

- **Disponibilidade:** monitor externo (Uptime Kuma, Zabbix etc.) em `https://DOMINIO/health/ready/`, a cada 1 minuto, com alerta para a TI. `/health/live/` só indica que o processo responde; `/ready/` também testa banco e cache.
- **Erros da aplicação:** configure `SENTRY_DSN` no `.env` (opcional; envia erros ao Sentry).
- **Backup:** alerte se o log do backup não registrar `backup ok` no dia.
- **Disco:** alerte acima de 80% (banco, backups e logs do Docker).
- **Logs:** a aplicação escreve JSON no stdout. Os logs não devem conter dados clínicos; se aparecer algum, trate como incidente (seção 9).

## 8. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Container `aegis_share` reinicia e o log diz "Ha migrations pendentes" | atualização sem migrate | faça backup e rode `docker compose run --rm aegis_share python manage.py migrate` |
| Container "unhealthy" | banco fora, erro de configuração | `docker compose logs aegis_share`; confira `postgres` com `docker compose ps` |
| "Bad Request (400)" | domínio fora de `ALLOWED_HOSTS` | inclua o nome usado no navegador e reinicie |
| "Forbidden (403) CSRF" ao enviar formulário | origem fora de `CSRF_TRUSTED_ORIGINS` | inclua `https://DOMINIO` (com porta, se não for 443) |
| Aviso de certificado no navegador | CA interna não instalada, ou DNS/`DOMAIN` divergentes | instale a CA (seção 2) e confira `DOMAIN` |
| Caddy não emite certificado (`acme`) | domínio não público ou portas 80/443 bloqueadas | use `CADDY_TLS=internal` ou libere as portas |
| Mapa de leitos não atualiza sozinho | WebSocket bloqueado ou Redis fora | confira `redis` no `docker compose ps`; proxies extras precisam repassar WebSocket |
| Usuário não vê um paciente | sem concessão de acesso | conceda em Patient access grants (seção 6) |
| Item do menu não aparece | falta permissão ou grupo | ajuste os grupos do usuário no Admin |
| Auditoria mostra o IP do proxy, não o do usuário | `TRUSTED_PROXY_IPS` sem a rede Docker | ajuste e recrie o container (`docker compose up -d`) |
| Páginas sem estilo | imagem construída sem estáticos | `docker compose build --no-cache aegis_share` e suba de novo |
| Usuários desconectados com frequência | expiração de 30 min sem uso (proposital) | ajuste `SESSION_IDLE_TIMEOUT_SECONDS`, se a política permitir |
| Erro 500 | falha da aplicação | veja os logs (ou o Sentry), anote o horário e abra um chamado (seção 10) |
| Disco cheio | backups ou logs do Docker | confira `BACKUP_KEEP_DAYS` e configure rotação de logs do Docker |

## 9. Segurança e chaves

| Segredo | Onde fica | Se perder |
|---|---|---|
| `SECRET_KEY` | `.env` | todas as sessões caem; gere outra |
| `FILE_ENCRYPTION_KEY` | `.env` | **2FA e arquivos da caixa laboratorial ficam ilegíveis** |
| `BACKUP_ENCRYPTION_KEY` | `.env` e cofre fora do servidor | **backups não abrem** |
| `POSTGRES_PASSWORD` | `.env` | redefina no PostgreSQL |

- Guarde cópias de `.env` e das chaves num cofre (gerenciador de senhas institucional), **nunca** junto dos backups.
- Não publique a porta 8000 na rede (`APP_BIND=127.0.0.1`); o acesso é só pelo proxy HTTPS.
- Aplique as atualizações de segurança: o repositório recebe PRs do Dependabot.
- **Incidente** (acesso indevido, vazamento, perda de dados): isole o servidor se necessário, preserve os logs e a auditoria, avise o encarregado de dados (DPO) do hospital. A LGPD prevê comunicação à ANPD e aos titulares quando houver risco relevante.

## 10. Como pedir ajuda

Abra uma issue no [repositório](https://github.com/ArcoverdePedro/AegisShare/issues) com:

- versão (`git log -1 --oneline`) e data da atualização;
- o que foi feito, o resultado esperado e o resultado obtido;
- trecho do log **sem dados de pacientes** (nomes, CPF, CNS, conteúdo clínico).

Vulnerabilidades de segurança **não** devem ir em issue pública: siga o [SECURITY.md](../SECURITY.md).
