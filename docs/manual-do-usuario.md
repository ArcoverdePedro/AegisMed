# Manual do usuário — AegisShare

Guia para quem usa o sistema no dia a dia: recepção, médicos, enfermagem, farmácia, laboratório, imagem, almoxarifado e administração. Para instalação, backup e problemas técnicos, veja o [Guia de suporte técnico](suporte-tecnico.md).

> O AegisShare está em desenvolvimento. Use com pacientes reais somente depois da homologação pela instituição e mantenha um procedimento de contingência em papel.

## Sumário

1. [Primeiro acesso](#1-primeiro-acesso)
2. [Conceitos importantes](#2-conceitos-importantes)
3. [Recepção: cadastro e agenda](#3-recepção-cadastro-e-agenda)
4. [Atendimento médico](#4-atendimento-médico)
5. [Internação e leitos](#5-internação-e-leitos)
6. [Prescrição e farmácia](#6-prescrição-e-farmácia)
7. [Enfermagem](#7-enfermagem)
8. [Laboratório](#8-laboratório)
9. [Imagem](#9-imagem)
10. [Estoque e compras](#10-estoque-e-compras)
11. [Administração](#11-administração)
12. [Limitações conhecidas](#12-limitações-conhecidas)
13. [Perguntas frequentes](#13-perguntas-frequentes)

---

## 1. Primeiro acesso

1. Abra o endereço do sistema informado pela TI (por exemplo, `https://his.seuhospital.gov.br`).
2. Entre com o usuário e a senha recebidos.
3. Vá em **seu nome (canto superior direito) → Segurança** e ative a **autenticação em dois fatores (2FA)** com um aplicativo como Google Authenticator, Microsoft Authenticator ou FreeOTP. **Guarde os códigos de recuperação** em local seguro: eles são mostrados uma única vez.
4. Em **Meu perfil** você pode trocar a foto.

**Sessão:** o sistema encerra a sessão depois de **30 minutos sem uso** e ao **fechar o navegador**. Em computador compartilhado, sempre use **Sair** ao terminar.

**Celular e tablet:** o sistema funciona no navegador e pode ser instalado como app ("Adicionar à tela inicial"). Ele **só funciona conectado** à rede do hospital.

## 2. Conceitos importantes

- **Paciente:** cadastro único, com CPF ou CNS e os dados exigidos pelo SUS.
- **Encontro:** cada atendimento (consulta ou internação). Evoluções, pedidos de exame, prescrições e sinais vitais pertencem a um encontro.
- **Acesso ao prontuário por vínculo:** um profissional só vê o paciente que **ele mesmo cadastrou** ou para o qual recebeu uma **concessão de acesso** (feita pela administração, com prazo opcional). Administradores veem todos. Ter um módulo no menu **não** dá acesso aos pacientes.
- **Nada é apagado:** evoluções recebem **adendos**, sinais vitais recebem **correções** e laudos/resultados recebem **retificações**. O registro original sempre fica visível.
- **Auditoria:** leituras e alterações de dados clínicos ficam registradas com usuário e horário.

O menu mostra apenas os módulos que o seu perfil permite. Se faltar algo de que você precisa, peça à administração.

## 3. Recepção: cadastro e agenda

### Cadastrar paciente

1. **Clínico → Pacientes → Novo paciente**.
2. Preencha identificação (CPF, CNS ou outro), nome completo, nascimento e sexo.
3. Em **Dados para o SUS**, informe **CNS**, **nome da mãe** (use "SEM INFORMAÇÃO" se desconhecido), **raça/cor** (autodeclarada), **nacionalidade** e **município**: digite parte do nome e escolha na lista (por exemplo, "Recife/PE"). A UF é preenchida pelo município.
4. Para raça/cor **Indígena**, escolha a **etnia**; para **naturalizado ou estrangeiro**, o **país de nascimento**.
5. Se o sistema avisar que existe outro cadastro com o **mesmo nome e nascimento**, confira antes de continuar. Cadastros nunca são unidos automaticamente.

Para corrigir contato, endereço ou dados SUS depois: abra o paciente → **Atualizar dados cadastrais**. Identificador, nome de registro e nascimento não são alterados por essa tela.

**Nome social** tem precedência na exibição; o nome de registro continua visível no prontuário.

### Agenda

- **Clínico → Agenda** mostra os horários do dia por profissional.
- **Abrir horários** (perfil de gestão da agenda): crie horários em lote para um profissional; é possível **bloquear** um horário com motivo.
- **Agendar:** abra o paciente → **Agendar consulta** → escolha o horário. Encaixe acima da capacidade exige permissão e justificativa.
- **Chegada:** na agenda, registre a chegada. Isso **abre o encontro** do paciente automaticamente.
- **Fila:** **Agenda → Fila** mostra quem chegou; use **Chamar** para chamar o paciente. Após o horário, é possível marcar **Falta**.
- Remarcar e cancelar exigem motivo e preservam o histórico.

## 4. Atendimento médico

1. Abra o paciente (**Clínico → Pacientes**) e o **encontro** em andamento. Se não houver, use **Novo encontro clínico**.
2. **Evolução:** no encontro, **Nova evolução**. Depois de salva, não é editada: abra a evolução e use **Registrar adendo** para complementar ou corrigir, informando o motivo.
3. **Lista de problemas:** no paciente → **Lista de problemas**. Registre diagnósticos com sistema de código (por exemplo, CID-10) e mantenha o estado atualizado.
4. A partir do encontro aberto, conforme seu perfil:
   - **Solicitar exame** (laboratório);
   - **Solicitar imagem**;
   - **Registrar consumo de material**.

## 5. Internação e leitos

- **Clínico → Leitos** mostra o **mapa de leitos** em tempo real: livre, ocupado, em higienização, bloqueado.
- **Admitir:** no mapa de leitos, **Nova admissão**: escolha o encontro e um leito livre da sua unidade.
- **Transferir:** no mapa, **Transferir** e escolha o novo leito.
- **Alta:** no mapa, **Registrar alta** → **Confirmar alta**. Isso encerra o encontro de internação e libera o leito, que vai para **higienização**.
- Após a higienização, a equipe responsável marca o leito como **disponível** pelo próprio mapa.
- Cada profissional vê os leitos das unidades a que tem acesso.

## 6. Prescrição e farmácia

**Médico:**

1. **Clínico → Prescrições → Nova prescrição**: escolha o encontro aberto do paciente, o medicamento do catálogo, dose, via, frequência e duração.
2. A prescrição começa como **rascunho**. Revise e use **Submeter** para enviar à farmácia.
3. Para interromper, **Cancelar** com motivo. Substituições ficam ligadas à prescrição anterior.

**Farmácia:**

1. **Clínico → Prescrições**: abra as prescrições submetidas e use **Validar**. O sistema mostra a revisão de segurança; quando faltam dados ou referências aprovadas, ela aparece como **não avaliável**, e a decisão é do farmacêutico.
2. **Dispensar:** escolha o **lote** e a quantidade. O estoque por lote é baixado e a dispensação fica registrada (repetir o envio não duplica).
3. **Catálogo de medicamentos** e **Estoque da farmácia** ficam no mesmo módulo, para quem tem permissão.

## 7. Enfermagem

- **Clínico → Enfermagem** lista os encontros acessíveis.
- **Sinais vitais:** no encontro → **Registrar sinais vitais**. Os valores são gravados nas unidades exibidas; o sistema não classifica normalidade. Para corrigir, use **Corrigir**: um novo registro substitui o anterior, que continua no histórico.
- **Administração de medicamentos:** no encontro → **Administrar medicações**. Só aparecem itens **dispensados** pela farmácia. Confirme paciente, medicamento e lote antes de registrar. Repetir o envio não duplica a administração.

## 8. Laboratório

1. **Pedido:** no encontro aberto → **Solicitar exame**.
2. **Coleta:** **Clínico → Laboratório** → abra o pedido → **Registrar coleta** (código da amostra e horário) e imprima a **etiqueta**.
3. **Recebimento** no laboratório: no detalhe de um pedido, **Recebimento de amostras** → **Confirmar recebimento**. Amostras inadequadas podem ser **rejeitadas** com motivo.
4. **Resultados:** registre o resultado da amostra e avance pelas etapas até a **liberação**. Correções depois da liberação geram uma **retificação** versionada.
5. **Caixa laboratorial:** recebe arquivos de equipamentos (até 1 MiB) de origens cadastradas. Os arquivos ficam cifrados e em quarentena; não viram resultado automaticamente.

## 9. Imagem

1. **Pedido:** no encontro aberto → **Solicitar imagem**.
2. **Clínico → Imagem** lista os pedidos.
3. **Laudo:** abra o pedido → registre o laudo → **Liberar**. Correções viram retificação versionada.

O sistema não armazena nem exibe as imagens (DICOM); registra pedidos e laudos.

## 10. Estoque e compras

- **Estoque:** catálogo de materiais (não medicamentos), **saldos** por local e lote e **movimentos** (entrada, saída, ajuste, estorno).
- **Requisições internas:** **Estoque → Requisitar material** para pedir material ao almoxarifado.
- **Consumo por paciente:** a partir do encontro (**Registrar consumo de material**).
- **Compras:** **Estoque → Compras → Novo pedido** (pedido de compra). A **aprovação** é feita por outra pessoa (perfil "Suprimentos · aprovação"). O **recebimento** gera a entrada no estoque uma única vez.

## 11. Administração

Disponível para perfis administrativos:

- **Cadastrar usuário:** seu nome → **Cadastrar usuário**.
- **Perfis e permissões:** **seu nome → Administração** (Admin do Django) → **Usuários** → adicione o usuário aos **grupos** (Recepção, Médico, Enfermagem, Farmácia, Laboratório, Imagem, Suprimentos, RH, Privacidade).
- **Acesso a pacientes:** no Admin, **Pep → Patient access grants** → adicione usuário, paciente, motivo e, se quiser, a data de expiração.
- **Catálogos:** exames de laboratório, exames de imagem, medicamentos, materiais, locais/leitos e origens da caixa laboratorial são cadastrados no Admin.
- **RH:** **RH** lista o cadastro funcional; conselho, registro e afastamentos são mantidos no Admin. Afastamentos bloqueiam a agenda do profissional.
- **Auditoria:** **Início → Auditoria** filtra por usuário, tipo de registro e ação.
- **Indicadores:** **Início → Indicadores**: ocupação de leitos, faltas, espera, rejeição de amostras e lotes vencidos.
- **LGPD:** **Clínico → Solicitações do titular** registra e acompanha pedidos de titulares de dados (acesso, correção etc.). Encerrar a solicitação não executa a ação pedida: isso segue o procedimento da instituição.
- **Exportar paciente:** gera o cadastro mínimo em FHIR (JSON) com recibo auditado.

## 12. Limitações conhecidas

- **Consulta ambulatorial não tem botão de encerrar.** O encontro de consulta continua "aberto"; só a alta de internação encerra encontros.
- **Agendar não dá acesso ao prontuário.** O médico da agenda precisa de uma concessão de acesso, a menos que tenha cadastrado o paciente.
- Ainda **não gera produção SUS** (BPA/AIH), não consulta CadSUS/RNDS e não emite receita ou atestado em PDF.
- Documentos **sem assinatura digital ICP-Brasil**: o prontuário eletrônico ainda não substitui o papel.
- **Só funciona com conexão.** Sem rede, o app mostra uma página de aviso e não guarda dados.

## 13. Perguntas frequentes

**Não encontro um paciente que sei que existe.**
Você só vê pacientes que cadastrou ou para os quais recebeu acesso. Peça a concessão à administração.

**Um item do menu sumiu.**
O menu depende das permissões do seu perfil. Fale com a administração.

**Fui desconectado no meio do trabalho.**
A sessão expira após 30 minutos sem uso. Entre novamente; o que já foi salvo continua no sistema. Formulários não enviados precisam ser preenchidos de novo.

**Errei uma evolução, sinal vital ou laudo.**
Não há exclusão. Use **Adendo**, **Corrigir** ou **Retificar**: o original fica no histórico com a correção ao lado.

**Perdi o celular com o 2FA.**
Use um dos códigos de recuperação. Se não tiver, a TI pode desativar o 2FA do seu usuário (veja o guia de suporte).

**Apareceu "Você está sem conexão".**
A rede caiu. Aguarde e clique em **Tentar novamente**. Use o procedimento em papel enquanto o sistema estiver fora.
