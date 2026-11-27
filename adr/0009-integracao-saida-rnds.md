# ADR-0009 — Integração de saída com a RNDS

## Status

Proposto em 2026-11-27, junto com a [extensão RNDS da spec 012](../specs/012-interoperabilidade/extensions/rnds/plan.md). O código existe, mas fica desligado (`RNDS_ENABLED=false`) até a homologação.

## Contexto

O Decreto 12.560/2025 e as portarias de 2026 preveem que estabelecimentos enviem dados à Rede Nacional de Dados em Saúde. A RNDS é um serviço FHIR R4 do Ministério da Saúde: o AegisMed precisa **chamar** a RNDS, autenticando-se com o certificado ICP-Brasil do estabelecimento.

O ADR-0004 proíbe **expor** API REST pública. Ele não trata de chamadas de saída.

## Decisão

- Permitir chamadas HTTP de saída **somente** para os hosts oficiais da RNDS (`ehr-auth*.saude.gov.br` e `*ehr-services*.saude.gov.br`), a partir de `apps/interoperability/rnds.py`.
- Nenhuma rota nova é exposta; o ADR-0004 continua valendo.
- O envio roda em lote pelo comando `manage.py rnds_send` agendado no cron do host, como o backup. Não há fila nova (Celery/Redis) nem envio dentro da requisição do usuário.
- O primeiro documento é o Resultado de Exame Laboratorial (REL v2.0), apenas para exames que o laboratório codificou no catálogo. Dado ausente bloqueia o envio com motivo técnico; nada é inferido.
- O certificado fica em arquivos PEM montados como segredo, fora do banco e do repositório. O token (30 min) fica só no cache e nunca vai para log.
- Respostas de erro são reduzidas ao status HTTP e aos códigos do `OperationOutcome`; `diagnostics` é descartado porque pode ecoar dados do paciente.

## Consequências

### Positivas
- atende à obrigação legal sem abrir superfície de entrada;
- reaproveita `requests`, `cryptography` (conversão do certificado fora da aplicação) e o cron já usado pelo backup;
- cada envio tem recibo (`RndsSubmission`) com estado, tentativas e código RNDS, consultável no Admin sem PHI.

### Negativas
- a latência até a RNDS depende do intervalo do cron;
- quem opera o servidor passa a custodiar o certificado do estabelecimento.

### Neutras
- a base dos systems FHIR (`https://rnds-fhir.saude.gov.br`) segue o guia v2.0; o guia antigo usa `http://www.saude.gov.br/fhir/r4`. A homologação confirma qual é aceito, e a troca é uma constante (`FHIR_BASE`).
