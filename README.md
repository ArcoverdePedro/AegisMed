# AegisShare

**Sistema de informação hospitalar (HIS) para hospitais de pequeno porte do SUS, construído em Django.**

O AegisShare reúne módulos clínicos e administrativos server-rendered: prontuário, agenda, ADT, prescrição/farmácia, enfermagem, laboratório, imagem, estoque e RH. A aplicação roda em Django/ASGI, usa PostgreSQL como fonte de verdade, Redis para Channels/cache e mantém segurança, rastreabilidade e minimização de dados como requisitos transversais.

> O projeto segue uma arquitetura Django monolítica e incremental, sem API REST pública (ADR 0004). Em 2026-11 foram removidos o produto original de troca de documentos (arquivos/IPFS, compartilhamento, chat, API `api/v1`), o centro cirúrgico, o faturamento particular, o piloto offline e o Web Push; o histórico continua no git.

## Estado atual

Os seguintes recortes estão implementados e protegidos pela CI:

- **Core:** usuários, 2FA TOTP, inventário e revogação de sessões, auditoria e health checks.
- **PEP:** pacientes, encontros clínicos, evolução e adendos append-only, autorização RBAC + ABAC e auditoria de acesso.
- **ADT:** localização/leitos, admissão, transferência e alta transacionais, mapa de leitos e atualização por Channels.
- **Prescrição/Farmácia:** catálogo, prescrição estruturada, revisão farmacêutica, estoque/lotes e dispensação idempotente.
- **Enfermagem:** sinais vitais estruturados, correção append-only e administração de medicamento, tudo online.
- **PWA:** app instalável (manifest/service worker), página offline genérica e limpeza de dados locais no logout.

A automação clínica é deliberadamente conservadora. Regras que dependem de conteúdo clínico institucional, assinatura jurídica ou semânticas operacionais ainda não aprovadas permanecem bloqueadas nas respectivas specs; o runtime não inventa decisões terapêuticas para preencher esses gaps.

## Recursos principais

### HIS clínico

- Paciente e `Encounter` canônicos reutilizados pelos módulos clínicos.
- Histórico clínico append-only, com correções/adendos preservando o fato anterior.
- RBAC por capacidades Django combinado com escopo clínico deny-by-default.
- ADT com prevenção de dupla ocupação ativa e operações transacionais de admissão, transferência e alta.
- Prescrição estruturada com ciclo DRAFT → submissão → validação farmacêutica e substituição rastreável.
- Safety engine determinístico que retorna `NOT_EVALUABLE` quando faltam fatos ou referências aprovadas, em vez de inferir regra clínica.
- Estoque farmacêutico por item/lote, ledger append-only e dispensação transacional/idempotente.
- Sinais vitais estruturados com unidades canônicas e registro de proveniência.
- Administração de medicamento vinculada à dispensação/lote, com `operation_key` idempotente e comportamento `network-only`.
- Eventos internos e audit log com payloads técnicos minimizados e sem PHI desnecessária.
- Playwright, Gherkin, axe-core, viewports de telefone/tablet e gates de privacidade local nas jornadas clínicas.

### Segurança

- 2FA TOTP com códigos de recuperação; inventário e revogação de sessões.
- `FILE_ENCRYPTION_KEY` (AES-256-GCM) protege os segredos de 2FA e os arquivos da caixa laboratorial.
- Audit log com `django-auditlog` e tela administrativa em `/auditoria/`.
- Sentry opcional, logging JSON e health checks.

### Plataforma

- PostgreSQL 18 e Redis.
- Django ASGI servido por Granian.
- Um único `compose.yml`.
- PWA com cache deny-by-default para superfícies sensíveis.
- CI com PostgreSQL, Redis, Ruff, migrations, suíte Django, Compose, Playwright, privacidade dos logs e Lighthouse.
- CodeQL e teste arquitetural que impede rotas públicas `/api/`.

## Arquitetura

```text
                         HTTPS
                           |
                    Reverse Proxy
                           |
                  +--------v---------+
                  |    AegisShare    |
                  | Django ASGI/HIS  |
                  |     Granian      |
                  +----+---------+---+
                       |         |
          +------------+         +----------------+
          |                                       |
   +------v------+                         +------v------+
   | PostgreSQL  |                         |    Redis    |
   | fonte de    |                         | Channels /  |
   | verdade     |                         | cache       |
   +-------------+                         +-------------+
```

Os módulos clínicos vivem no mesmo monólito Django e reutilizam identidades canônicas em vez de criar cadastros paralelos. Redis é usado por Channels e cache. Sem Redis, esses componentes usam memória local e a aplicação força um único worker para manter consistência.

## Especificações e decisões arquiteturais

O desenvolvimento clínico é orientado por specs versionadas e ADRs no próprio repositório:

```text
specs/000-core/                    núcleo, segurança e fronteiras arquiteturais
specs/001-pep/                     prontuário eletrônico do paciente
specs/002-adt/                     admissão, transferência, alta e leitos
specs/003-prescricao-farmacia/     prescrição, safety review, estoque e dispensação
specs/004-enfermagem/              sinais vitais e administração de medicamento
specs/005-lis/                     pedidos laboratoriais e coleta manual
specs/006-ris-pacs/                pedidos de imagem (RIS v1)
specs/009-estoque-compras/          catálogo e requisições de materiais
specs/010-rh-escalas/               cadastro funcional mínimo implementado
specs/012-interoperabilidade/       exportação FHIR e caixa laboratorial cifrada
specs/014-pwa/                     PWA instalável (offline e push removidos)
adr/                               decisões arquiteturais aceitas
```

Cada spec mantém requisitos, contratos, tarefas e rastreabilidade. Gates dependentes de governança externa permanecem marcados como `BLOCKED` e não são implementados silenciosamente.

A [Spec 012 — Interoperabilidade por arquivos](specs/012-interoperabilidade/spec.md) implementa exportação individual de cadastro mínimo em FHIR R4 JSON, com autorização PEP e recibo auditado. Consulte o [guia operacional](docs/interoperabilidade.md). A ingestão HL7/ASTM necessária ao LIS será uma extensão posterior.

[Spec 013 — Solicitações do titular](specs/013-lgpd-anvisa/spec.md) implementada, com registro, análise e encerramento administrativo auditáveis. Consulte o [guia operacional](docs/solicitacoes-titular.md) para migrations e permissões. Não automatiza exclusão, anonimização, retenção ou decisões jurídicas.

[Spec 005 — LIS v1](specs/005-lis/spec.md) implementa pedidos e coleta manual, com catálogo institucional, escopo PEP e auditoria. Consulte o [guia operacional](docs/laboratorio.md). Ingestão HL7/ASTM e resultados permanecem em etapa posterior.

Implementado: [caixa laboratorial cifrada em quarentena](specs/012-interoperabilidade/extensions/lab-inbox/spec.md), com escopo por origem e deduplicação, sem interpretação ou liberação de resultados. Aprovada em 2026-09-18. [Guia operacional](docs/caixa-laboratorial.md) e [evidências](specs/012-interoperabilidade/extensions/lab-inbox/validation.md).


[Spec 006 — pedidos de imagem (RIS v1)](specs/006-ris-pacs/spec.md) aprovada e implementada em 2026-09-18, com catálogo institucional, escopo PEP, snapshots e reenvios auditados. [Guia operacional](docs/imagem.md) e [evidências](specs/006-ris-pacs/validation.md). DICOM, viewer e laudos dependem de extensões com contratos próprios.

[Spec 009 — catálogo e requisições de materiais](specs/009-estoque-compras/spec.md) autorizada e implementada em 2026-09-18, com catálogo não medicamentoso, snapshots, quantidades inteiras e consulta institucional por capacidade. [Guia operacional](docs/estoque-requisicoes.md) e [evidências](specs/009-estoque-compras/validation.md). Não duplica o estoque farmacêutico nem confirma compra, reserva ou entrega.

[Spec 010 — cadastro funcional mínimo](specs/010-rh-escalas/spec.md) autorizada e implementada em 2026-09-28, com setor/função/status cadastral vinculados ao usuário existente, gestão pelo Admin e consulta institucional por capacidade. [Guia operacional](docs/cadastro-funcional.md) e [evidências](specs/010-rh-escalas/validation.md). Sem escalas, ponto ou efeitos sobre autenticação.

## Requisitos

- Docker e Docker Compose para o deploy recomendado.
- Python 3 disponível no host apenas para o gerador independente de segredos, se desejar usá-lo.
- `SECRET_KEY` e `FILE_ENCRYPTION_KEY` fortes.
- HTTPS/reverse proxy em produção.

## Primeira configuração

Copie o exemplo e instale os segredos diretamente no `.env` antes de iniciar o Django:

```bash
cp .env-example .env
python3 scripts/generate_secrets.py --install-env .env
```

O modo `--install-env` substitui somente `SECRET_KEY` e `FILE_ENCRYPTION_KEY` vazias ou marcadas como `CHANGE_ME`, preserva valores válidos já existentes, recusa definições duplicadas e deixa o arquivo com permissão `0600`. Os segredos **não são impressos no terminal**.

Depois configure os demais campos do `.env`, principalmente:

```env
POSTGRES_PASSWORD=...
ALLOWED_HOSTS=his.exemplo.gov.br
CSRF_TRUSTED_ORIGINS=https://his.exemplo.gov.br
```

Se preferir entregar os segredos a um gerenciador externo sem alterar `.env`, o comportamento anterior continua disponível:

```bash
python3 scripts/generate_secrets.py
```

Esse comando cria `.secrets.generated.env` com permissão `0600`; copie o conteúdo para o gerenciador de segredos e remova o arquivo temporário quando terminar. Não use `--force` em produção sem uma decisão explícita de rotação de chaves.

Para produção atrás de HTTPS mantenha:

```env
DEBUG=false
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

Depois construa, aplique as migrations e suba a stack:

```bash
docker compose build
docker compose run --rm aegis_share python manage.py migrate
docker compose up -d
```

No primeiro acesso, se ainda não houver administrador, `/setup/` permite criar o primeiro superusuário.

## Docker Compose

Uma única stack: Django + PostgreSQL + Redis.

PostgreSQL e Redis ficam somente na rede Docker. A aplicação publica a porta só em `127.0.0.1` (`APP_BIND`); o acesso pela rede passa pelo proxy HTTPS.

### HTTPS com o proxy Caddy

O perfil `proxy` adiciona um Caddy na frente da aplicação, com certificado automático:

```env
DOMAIN=his.hospital.gov.br
CADDY_TLS=acme          # domínio público: certificado Let's Encrypt
# CADDY_TLS=internal    # nome só da rede interna: CA própria do Caddy
TRUSTED_PROXY_IPS=172.16.0.0/12   # rede Docker, para registrar o IP real do usuário
```

```bash
docker compose --profile proxy up -d
```

Com `CADDY_TLS=internal`, instale nas estações a CA raiz do Caddy (`docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt .`). Sem o perfil, coloque outro proxy HTTPS na frente da porta `127.0.0.1:8000`.

### Atualização de versão

1. Leia as notas de atualização no [CHANGELOG](CHANGELOG.md).
2. Faça backup (`scripts/backup.sh`).
3. `git pull && docker compose build`
4. `docker compose run --rm aegis_share python manage.py migrate`
5. `docker compose up -d`

O container recusa iniciar se houver migration pendente, para que código novo nunca rode sobre o banco antigo.

A stack atual usa PostgreSQL 18 e monta o volume em `/var/lib/postgresql`, conforme o layout das imagens oficiais 18+. **Não conecte diretamente um volume criado por PostgreSQL 17 ou anterior a uma imagem PostgreSQL 18.** Faça backup/restauração ou um procedimento de `pg_upgrade` apropriado antes de uma mudança de versão principal.

Para usar um PostgreSQL ou Redis já existentes, crie um `compose.override.yml` que redefina `DATABASE_URL`/`REDIS_URL` do serviço `aegis_share` (o Compose o aplica automaticamente). Sem Redis, o entrypoint reduz `WEB_WORKERS` para `1`.

## Inicialização do container

O entrypoint normal:

1. aguarda o banco responder;
2. confere se há migrations pendentes e, se houver, para com instruções (ou as aplica com `RUN_MIGRATIONS=true`, só para desenvolvimento/CI);
3. inicia Granian/ASGI como usuário sem privilégios (`aegis`, uid 10001).

Quando um comando é fornecido explicitamente com `docker compose run aegis_share <comando>`, o entrypoint executa somente esse comando. Isso permite usar `manage.py`, scripts e rotinas administrativas sem iniciar o servidor.

As opções do processo web podem ser controladas por:

```env
RUN_MIGRATIONS=false
WEB_WORKERS=2
DB_STARTUP_ATTEMPTS=30
```

## Variáveis de ambiente

| Variável | Uso |
|---|---|
| `SECRET_KEY` | segredo criptográfico do Django |
| `FILE_ENCRYPTION_KEY` | chave-mestra dos segredos de 2FA e da caixa laboratorial |
| `POSTGRES_DB` | banco do PostgreSQL interno |
| `POSTGRES_USER` | usuário do PostgreSQL interno |
| `POSTGRES_PASSWORD` | senha do PostgreSQL interno |
| `DATABASE_URL` | conexão direta quando Django roda fora do compose |
| `REDIS_URL` | Redis direto quando Django roda fora do compose |
| `FILE_MAX_UPLOAD_MB` | limite de upload |
| `SENTRY_DSN` | Sentry opcional |
| `WEB_WORKERS` | workers Granian |
| `RUN_MIGRATIONS` | `false` em produção; migrations rodam como passo explícito |
| `SESSION_IDLE_TIMEOUT_SECONDS` | sessão expira após esse tempo sem uso (padrão 1800) e ao fechar o navegador |
| `APP_BIND` / `APP_PORT` | endereço e porta publicados da aplicação (padrão `127.0.0.1:8000`) |
| `DOMAIN`, `CADDY_TLS`, `HTTP_PORT`, `HTTPS_PORT` | proxy HTTPS do perfil `proxy` |
| `TRUSTED_PROXY_IPS` | IPs/redes do proxy autorizados a informar o IP do cliente |
| `BACKUP_KEEP_DAYS` | dias de retenção do `scripts/backup.sh` (padrão 30; 0 desativa) |

Consulte `.env-example` para a configuração completa.

## Backup e restauração

`scripts/backup.sh <destino>` gera, para a stack `compose.yml`, o arquivo `db-*.dump.aegisbak` (`pg_dump -Fc`) cifrado com `BACKUP_ENCRYPTION_KEY` (AES-256-GCM em blocos; corrupção, troca de ordem ou truncamento falham na abertura). Ele é aberto e autenticado antes de perder o sufixo `.partial`; um `SHA256SUMS-*` acompanha o lote.

Gere a chave uma vez e guarde-a fora do servidor, separada do backup e da `FILE_ENCRYPTION_KEY` (precisam ser diferentes):

```bash
python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

Sem `BACKUP_ENCRYPTION_KEY` o backup não abre; sem `FILE_ENCRYPTION_KEY` os segredos de 2FA e a caixa laboratorial restaurados não decifram. Restauração em banco novo/vazio:

```bash
python manage.py backup_open < db-STAMP.dump.aegisbak | pg_restore --no-owner -d NOVO_BANCO
```

Agende o backup diário no servidor (exemplo com cron, às 2h, retendo 30 dias):

```cron
0 2 * * * cd /opt/aegisshare && BACKUP_KEEP_DAYS=30 scripts/backup.sh /srv/backups/aegisshare >> /var/log/aegisshare-backup.log 2>&1
```

O script só apaga lotes antigos depois que o lote novo foi aberto e conferido. Copie o diretório de backup para fora do servidor (outro prédio ou nuvem) e ensaie uma restauração em banco vazio pelo menos uma vez por mês. Pendentes (G11): RPO/RTO e local da cópia externa.

## Auditoria

O projeto usa `django-auditlog` para alterações e eventos de acesso. Campos sensíveis, como hashes de tokens, segredo TOTP, chave protegida do arquivo e medidas clínicas explicitamente excluídas dos contratos de auditoria, não são copiados indiscriminadamente para o histórico.

Administradores podem consultar:

```text
/auditoria/
```

A interface permite filtrar por ator, modelo e ação.

## PWA

O AegisShare pode ser instalado como app (manifest + service worker), mas funciona só online: o service worker guarda apenas o shell e uma página offline genérica, nunca conteúdo clínico. O logout envia `Clear-Site-Data` e apaga dados locais, inclusive filas do antigo piloto offline em navegadores que já o usaram.

## Health checks

```text
/health/live/      processo HTTP vivo
/health/ready/     banco e cache prontos
/health/services/  diagnóstico de configuração (banco, Redis)
```

Aponte um monitor externo (Uptime Kuma, Zabbix ou similar) para `https://DOMINIO/health/ready/` com alerta para a equipe de TI, e configure `SENTRY_DSN` para receber erros da aplicação.

## Desenvolvimento

```bash
uv sync --dev
uv run python manage.py migrate
uv run python manage.py runserver
```

Validações:

```bash
uv run ruff check aegis_share apps mysite
uv run ruff format --check aegis_share apps mysite
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py test --verbosity 2
```

O CI executa o lint sem `--fix`; o checkout precisa estar limpo antes do merge.

## Manutenção

O Dependabot mantém dependências Python, GitHub Actions e imagens Docker sob atualização automática; os PRs passam pela CI antes de qualquer merge automático.

## Segurança

Leia [SECURITY.md](SECURITY.md) antes de publicar uma instalação na internet. Para alterações no código, consulte também [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md) e [CHANGELOG.md](CHANGELOG.md).

## Licença

AegisShare é distribuído sob a **GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)**. Consulte o texto integral em [LICENSE](LICENSE).
