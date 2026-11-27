# Extensão 012 — Plano de adequação à RNDS

## Status

**Proposta em 2026-11-27.** Este documento organiza o que o hospital e o código precisam para enviar dados à Rede Nacional de Dados em Saúde (RNDS).

**Código pronto para homologação (branch `feat/rnds`, 2026-11-27), desligado por padrão:**
- F1 (dados mestres) está implementada.
- F2 e F3 estão implementadas para o REL v2.0. Guia operacional: [docs/rnds.md](../../../../docs/rnds.md); decisão: [ADR-0009](../../../../adr/0009-integracao-saida-rnds.md).

**Ainda dependem do hospital ou do DATASUS:**
- F0: credenciamento, certificado e identificador do solicitante.
- Homologação real e pedido de produção.
- Codificação GAL do catálogo pelo laboratório (G07).
- F5 (CMD).

## Contexto normativo

- O **Decreto 12.560/2025** prevê o envio de dados à RNDS por estabelecimentos públicos e privados, conforme os modelos padronizados.
- A **Portaria GM/MS 11.952/2026** (13/07/2026) instituiu o modelo de informação do **Conjunto Mínimo de Dados (CMD)**: identificação da pessoa (CPF ou CNS), contato assistencial (estabelecimento, admissão, desfecho e CPF do profissional responsável), diagnósticos (CID ou CIAP), dados oncológicos e procedimentos (Tabela SUS, entre outras).
- Segundo fonte de terceiro (P2 Saúde, 20/11/2026), a **Portaria GM/MS 12.511/2026** prevê a substituição **gradual** de BPA, APAC, RAAS, SISAIH01, CIHA, SIA e SIH pelo CMD, em nove fases e sem prazo único. Hospitais com SISAIH01/SIH ficam na **última** fase. O cronograma e as regras técnicas do DATASUS ainda não foram publicados. **Este ponto precisa ser conferido no DOU**: a leitura do texto oficial falhou em 2026-11-27.
- Consequência para o AegisMed: o faturamento SUS tende a convergir para o CMD. BPA/AIH como arquivos isolados não devem receber investimento antes de o cronograma sair.

## O que a RNDS exige (guia oficial)

- **Credenciamento:** feito pelo gestor do estabelecimento no Portal de Serviços do DATASUS, com conta gov.br e certificado ICP-Brasil (e-CNPJ do estabelecimento ou e-CPF do gestor, A1 ou A3). O certificado informado no pedido deve ser o mesmo usado na autenticação.
- **Identificador do solicitante:** fornecido pela RNDS quando o acesso é aprovado. Não é o CNES. Compõe o identificador de cada documento enviado (`BRRNDS-{identificador}`).
- **Autenticação:** token obtido com o certificado em mTLS (`ehr-auth-hmg.saude.gov.br` na homologação, `ehr-auth.saude.gov.br` na produção), válido por 30 minutos. As chamadas levam `X-Authorization-Server: Bearer <token>` e `Authorization: <CNS do profissional>` lotado no estabelecimento.
- **Endereços:** a homologação tem um endereço único (`ehr-services.hmg.saude.gov.br`). Em produção há um endereço por UF (`xx-ehr-services.saude.gov.br`), definido pela UF do CNES. Produção não pode ser usada para testes.
- **Serviços:** `GET /api/token`; consultas `Patient`, `Organization`, `Practitioner` e `PractitionerRole`; `POST Bundle` para enviar ou substituir resultado de exame (a substituição usa `relatesTo`).
- **Homologação:** exige PDF de evidências com o Bundle enviado, a captura de tela do validador oficial aprovando o Bundle e o código que a RNDS atribuiu ao documento (cabeçalhos `location`/`content-location`). Esse código também precisa ser guardado para substituições.
- **Resultado de Exame Laboratorial (REL):** o exemplo oficial v2.0 é um Bundle `document` com `Composition`, `Observation` e `Specimen`, **sem `Condition`**. A página do modelo computacional, ainda em rascunho, cita também `Condition`; a implementação segue o exemplo v2.0. Os modelos documentados são de exames de notificação (COVID-19, Monkeypox).
  - O código do exame vem da **tabela GAL para laboratórios públicos**; LOINC é para laboratórios privados.
  - A amostra usa `BRTipoAmostraGAL` e a categoria usa o subgrupo da Tabela SUS.
  - Datas devem ter fuso explícito.

## Lacunas no AegisMed

| Exigência | Situação |
|---|---|
| CNS/CPF do paciente | Existe e é validado (`apps/clinical/pep/validators.py`) |
| CNES, CNPJ e UF do estabelecimento | Não existem |
| CNS, CPF e CBO do profissional | Não existem; `apps/admin/hr` só guarda conselho e registro |
| Exames com código GAL, amostra GAL e subgrupo SUS | Não existem; catálogo institucional sem codificação (G07) |
| Suspeita diagnóstica e CID | Bloqueados (G03/H04) |
| Saída HTTP com mTLS | `requests` e `cryptography` já estão instalados (converter .pfx em PEM com `cryptography.pkcs12`) |
| Envio idempotente com recibo | O padrão de recibo da spec 012 (`PatientExportReceipt`) serve de modelo |

## Fases

### F0 — Governança e credenciais (hospital, sem código)

Responsáveis: direção, gestor do CNES, TI e encarregado de dados (LGPD).

1. Nomear o gestor RNDS e o integrador técnico.
2. Adquirir o certificado ICP-Brasil. A recomendação é e-CNPJ A1, porque o servidor precisa usá-lo sem interação humana. Registrar validade e responsável pela renovação.
3. Conta gov.br do gestor e pedido de acesso à **homologação** no Portal de Serviços, informando a faixa de IPs de saída do servidor.
4. Registrar no inventário de dados (`docs/his/INVENTARIO_DADOS.md`) a base legal do envio (cumprimento de obrigação legal ou regulatória) e o novo compartilhamento com o Ministério da Saúde (G10).
5. Decidir o **primeiro caso de uso**. Recomendação: REL de exames de notificação, se o laboratório do hospital os realiza; caso contrário, aguardar o CMD.

Pronto quando: identificador do solicitante recebido e caso de uso aprovado em `DECISOES.md`.

### F1 — Dados mestres (código pequeno, sem dependência de credencial)

1. CNES, CNPJ e UF do estabelecimento como configuração de ambiente (`django-environ`, já usado). Não criar model de instituição enquanto houver um único hospital (G01).
2. CNS, CPF e CBO no cadastro funcional (`apps/admin/hr.Employee`), validando o CNS com o `validate_cns` existente. A tabela CBO entra pelo mesmo padrão de `update_sus_tables`, se a fonte for pública e licenciável.
3. Codificação GAL, amostra GAL e subgrupo SUS no catálogo de exames, preenchida pelo laboratório (G07).

Pronto quando: os dados existirem, validados por teste, sem nenhum envio.

### F2 — Cliente RNDS em homologação

1. **ADR 0009 — integração de saída com a RNDS.** O ADR 0004 proíbe API recebendo chamadas; este ADR registra que chamadas de saída para a RNDS são aceitas, e só para ela.
2. Um módulo `apps/interoperability/rnds.py` com funções simples:
   - obter o token com o certificado, guardando-o em cache por menos de 30 minutos e nunca registrando-o em log;
   - montar o Bundle a partir de dados já liberados;
   - enviar e devolver o código da RNDS.
3. O certificado fica em arquivo montado como segredo do Docker, com a senha em variável de ambiente; nunca vai para o banco nem para o repositório. Configurações: `RNDS_ENV` (hmg/prod), `RNDS_CERT_PATH`, `RNDS_CERT_PASSWORD`, `RNDS_REQUESTER_ID`.
4. Um model `RndsSubmission` append-only, com documento de origem, `operation_key`, estado, código RNDS, tentativas e erro técnico sem PHI. A constraint única garante que o mesmo resultado não seja enviado duas vezes.
5. Reenvio por `manage.py rnds_send_pending`, agendado no cron do host. Sem Celery ou fila nova.
6. Validação local dos Bundles com o validador oficial em CI opcional. A biblioteca `Voa-Health/rnds` (Apache-2.0, cliente ainda *alpha*) fica como referência de leitura, não como dependência.

Pronto quando: um Bundle sintético for aceito na homologação e o PDF de evidências estiver gerado.

### F3 — Primeiro envio real (REL)

1. Disparo apenas para resultados com status **liberado** de exames marcados como notificáveis no catálogo.
2. O cabeçalho `Authorization` usa o CNS do profissional que liberou o resultado; sem CNS, o envio fica pendente, com alerta para a equipe.
3. Retificação de resultado gera substituição (`relatesTo` → `Composition/{código RNDS}`).
4. Tela administrativa só com metadados (estado, data, código RNDS), no padrão da caixa laboratorial.
5. Pedido de produção com o PDF de evidências.

Pronto quando: o DATASUS liberar a produção e o primeiro envio real for confirmado.

### F4 — Produção e operação

- Endereço EHR da UF do CNES; alerta de envios pendentes há mais de 24 h; aviso de vencimento do certificado com 30 dias de antecedência.
- Runbook em `docs/suporte-tecnico.md`: renovar o certificado, trocar de ambiente e reprocessar pendências.

### F5 — CMD (quando o DATASUS publicar as regras técnicas)

- Mapear `Encounter`, `Admission` e `Discharge` para o contato assistencial (admissão, desfecho, profissional responsável).
- Depende de CID (G03/H04) e de procedimentos da Tabela SUS (G09).
- É também o caminho do futuro faturamento SUS; a convergência deve ser reavaliada quando o cronograma da Portaria 12.511 sair.

## Riscos

- **Vazamento do certificado:** permite enviar em nome do hospital. Mitigação: arquivo de segredo com ACL, sem cópia no banco ou em backups públicos, e revogação documentada.
- **PHI em logs:** Bundles e tokens nunca são registrados; o erro guardado é só técnico.
- **Normas em movimento:** as portarias de 2026 ainda terão regulamentação técnica. Rever este plano a cada portaria nova.
- **Escopo do REL:** se o laboratório do hospital não realiza exames de notificação, o F3 não se aplica e o primeiro envio real passa a ser o CMD.

## Pendências desta pesquisa

- Ler no DOU o texto integral das Portarias 11.952/2026 e 12.511/2026 (a leitura falhou em 2026-11-27).
- Ler a página "Colocar em produção" do guia RNDS e confirmar os critérios de aprovação.
- Confirmar com o gestor estadual se o hospital já está em alguma fase de envio obrigatório.

## Fontes

- Guia RNDS: [gestor](https://rnds-guia.saude.gov.br/docs/publico-alvo/gestor/gestor/), [certificado](https://rnds-guia.saude.gov.br/docs/publico-alvo/gestor/certificado/), [portal](https://rnds-guia.saude.gov.br/docs/publico-alvo/gestor/portal/), [identificador](https://rnds-guia.saude.gov.br/docs/publico-alvo/gestor/identificador/), [serviços](https://rnds-guia.saude.gov.br/docs/rnds/servicos/), [ambientes](https://rnds-guia.saude.gov.br/docs/rnds/ambientes/), [conheça os serviços](https://rnds-guia.saude.gov.br/docs/publico-alvo/ti/conhecer/), [homologar](https://rnds-guia.saude.gov.br/docs/publico-alvo/ti/homologar/), [modelo computacional do REL](https://rnds-guia.saude.gov.br/docs/rel/mc-rel/)
- [Guia FHIR da RNDS: artefatos](https://rnds-fhir.saude.gov.br/artifacts.html)
- [Decreto 12.560/2025](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/decreto/d12560.htm)
- [Portaria GM/MS 7.495/2025](https://legismap.com.br/leis-e-normas/portaria-gm-ms-n-7-495-de-04-08-2025)
- P2 Saúde (terceiro): [Portaria 11.952/2026](https://p2saude.com.br/portaria-11952-2026-conjunto-minimo-dados-cmd/) e [CMD substitui BPA/APAC/AIH](https://p2saude.com.br/conjunto-minimo-dados-cmd-substitui-bpa-apac-aih/)
- [Voa-Health/rnds](https://github.com/Voa-Health/rnds)
