# RNDS — envio de resultados de exame

Guia operacional do envio à Rede Nacional de Dados em Saúde. O plano completo, as fontes e o que ainda depende do hospital estão em [specs/012-interoperabilidade/extensions/rnds/plan.md](../specs/012-interoperabilidade/extensions/rnds/plan.md). A decisão de arquitetura está no [ADR-0009](../adr/0009-integracao-saida-rnds.md).

**Hoje o AegisMed envia só o Resultado de Exame Laboratorial (REL v2.0).** O envio vem desligado e só deve ser ligado depois do credenciamento.

## 1. Antes de ligar (hospital)

1. Gestor responsável com conta gov.br.
2. Certificado ICP-Brasil do estabelecimento (e-CNPJ A1 recomendado), o mesmo informado no pedido.
3. Pedido de acesso à **homologação** no [Portal de Serviços do DATASUS](https://servicos-datasus.saude.gov.br/), informando o IP de saída do servidor.
4. Guardar o **identificador do solicitante** que a RNDS fornece na aprovação (não é o CNES).

## 2. Dados que o AegisMed precisa

| Onde | O quê | Quem preenche |
|---|---|---|
| `.env` | CNES e UF do estabelecimento | TI |
| Admin › Cadastro funcional | **CNS** do profissional (também CPF e CBO, para o CMD futuro) | RH |
| Admin › Laboratório › Exames | Tabela (GAL para laboratório público), código do exame, tipo de amostra GAL, subgrupo da Tabela SUS (4 dígitos), tipo de resultado | Laboratório |
| Cadastro do paciente | **CNS** (a RNDS identifica o indivíduo só pelo CNS) | Recepção |

Os cinco campos RNDS do exame são "todos ou nenhum". Exame sem codificação **não é enviado**.

Resultado **qualitativo** precisa estar escrito como `Detectável`, `Não detectável` ou `Inconclusivo` (maiúsculas e acentos não importam). Resultado **quantitativo** precisa ser número. Fora disso, o envio fica bloqueado e o motivo aparece no Admin.

## 3. Certificado no servidor

Converta o `.pfx` em PEM **fora** do repositório e proteja os arquivos:

```bash
openssl pkcs12 -in certificado.pfx -clcerts -nokeys -out /srv/aegismed/secrets/rnds.crt
openssl pkcs12 -in certificado.pfx -nocerts -nodes -out /srv/aegismed/secrets/rnds.key
chmod 600 /srv/aegismed/secrets/rnds.*
```

Monte a pasta no container com um `compose.override.yml`:

```yaml
services:
  aegis_med:
    volumes:
      - /srv/aegismed/secrets:/run/secrets/aegismed:ro
```

A chave fica sem senha porque a aplicação precisa usá-la sem interação. Por isso: permissão `0600`, nenhuma cópia em backup público e revogação imediata do certificado se o servidor for comprometido.

## 4. Configuração (`.env`)

```env
RNDS_ENABLED=true
RNDS_ENVIRONMENT=hmg            # prod só depois da aprovação do DATASUS
RNDS_REQUESTER_ID=<identificador do solicitante>
RNDS_CERT_FILE=/run/secrets/aegismed/rnds.crt
RNDS_KEY_FILE=/run/secrets/aegismed/rnds.key
RNDS_SEND_SINCE=2026-12-01      # resultados liberados antes não são enviados
ESTABLISHMENT_CNES=1234567
ESTABLISHMENT_UF=PE
```

Com `RNDS_ENABLED=true`, a aplicação não sobe se faltar algum desses valores. Em produção, o endereço de envio é escolhido pela UF do CNES.

## 5. Conferir antes de enviar

```bash
docker compose run --rm aegis_med python manage.py rnds_send --dry-run
```

Mostra quantos resultados estão prontos e por que os demais estão bloqueados. Não grava nem envia nada e funciona com a RNDS desligada.

## 6. Envio agendado

Agende no cron do host (`crontab -e` do usuário que opera o Docker), por exemplo a cada 10 minutos:

```cron
*/10 * * * * cd /opt/aegismed && docker compose run --rm aegis_med python manage.py rnds_send >> /var/log/aegismed-rnds.log 2>&1
```

Cada execução:
1. Registra um envio para cada resultado **liberado** de exame codificado desde `RNDS_SEND_SINCE`.
2. Envia os pendentes, repete as falhas (até 10 tentativas) e reavalia os bloqueados, que seguem automaticamente quando o dado que faltava é preenchido.
3. Retificação de resultado já enviado vai como **substituição** do documento anterior (mesmo identificador, `relatesTo`). Resultado retificado antes do envio fica bloqueado e só a versão nova é enviada.

Duas execuções ao mesmo tempo não enviam em dobro. Um envio interrompido há mais de 15 minutos volta a ser tentado.

Depois de esgotar as 10 tentativas, corrija a causa e rode `manage.py rnds_send --reset-failed`.

## 7. Acompanhar

Admin › Interoperabilidade › **Envios RNDS**: data, situação, ambiente, tentativas, código RNDS e motivo técnico. A tela é somente leitura e não mostra dado do paciente nem do resultado.

## 8. Homologação

O DATASUS pede um PDF de evidências para liberar a produção, com:
1. o Bundle de um exame enviado com sucesso na homologação;
2. a captura de tela do validador oficial aprovando esse Bundle;
3. o código atribuído pela RNDS (coluna "Código RNDS" no Admin).

Na homologação, confirme também a base dos systems FHIR (constante `FHIR_BASE` em `apps/interoperability/rnds.py`) e o system do identificador do documento (`BRRNDS-<identificador>`). Os guias oficiais divergem nesses dois pontos.
