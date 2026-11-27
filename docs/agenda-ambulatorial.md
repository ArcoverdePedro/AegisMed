# Agenda ambulatorial, chegada e fila (H11)

App `apps/clinical/scheduling`, FBVs em `/agenda/`. Escopo provisório (G01 pendente): ambulatório de hospital geral. Não registra dado clínico; a chegada abre o `Encounter` canônico do PEP.

## Capacidades

| Permissão (`scheduling.*`) | Uso |
| --- | --- |
| `view_agenda` | agenda do dia, fila e detalhe (detalhe exige também acesso ao paciente no PEP) |
| `manage_agenda` | abrir horários em lote (até 96 por vez, idempotente por profissional+início) e bloquear com motivo |
| `book_appointment` | agendar a partir do prontuário ("Agendar consulta"), remarcar e cancelar com motivo |
| `overbook_appointment` | encaixe acima da capacidade, com justificativa |
| `checkin_appointment` | chegada, chamada e falta (falta só após o início do horário) |
| `view_call_panel` | painel de chamada da TV (`/agenda/painel/`), somente senha, local e hora |

## Regras

- Capacidade verificada com o horário travado (`select_for_update`); disputa pela última vaga gera um agendamento e um conflito (teste PostgreSQL). Mesmo paciente não fica ativo duas vezes no mesmo horário (constraint parcial). `operation_key` torna o envio repetido idempotente.
- Estados: Agendado → Chegou → Chamado; Agendado → Cancelado/Remarcado/Falta. Remarcar cria novo agendamento ligado ao anterior (`rescheduled_from`), que fica "Remarcado" — histórico preservado.
- Chegada cria um único `Encounter` (consulta, local do horário, profissional do horário como responsável) e emite `encounter.created` após o commit.
- Bloquear horário não cancela agendamentos existentes: a tela orienta remarcar.
- Privacidade: nomes só aparecem a quem já acessa o paciente pelas regras do PEP; demais veem a senha curta. Rotas `/agenda/` são `private, no-store`. Não há confirmação externa (sem canal autorizado).

## Painel de chamada (TV)

- A conta da TV é fixa: **`aegis.expositor`**. Na instalação, a tela seguinte à criação do primeiro administrador define a senha dela; depois, um administrador troca a senha em `/agenda/conta-do-painel/` (item "Senha do expositor" no menu do usuário, só para administradores; também linkado na fila). O nome não muda e é reservado nos formulários de cadastro.
- Salvar a senha reimpõe o perfil mínimo: FUNC, sem grupos e só com `scheduling.view_call_panel`. Ele não vê agenda, fila nem PEP.
- A sessão da TV não expira por inatividade nem ao fechar o navegador (10 anos). Para desconectar a TV, troque a senha: as sessões abertas caem na hora.
- `CallPanelKioskMiddleware` prende a conta ao painel: qualquer outro endereço redireciona para ele (só logout, estáticos e PWA passam).
- A tela mostra a senha curta (derivada do id do agendamento), o consultório e a hora das últimas 6 chamadas do dia. Nome do paciente e do profissional nunca aparecem; o paciente nem é consultado.
- Atualização por Channels (`/ws/clinical/scheduling/call-panel/`): o socket só avisa "houve chamada", sem dados; a TV refaz o GET autorizado do fragmento. Há também uma atualização a cada 30 s caso o socket caia.
- A permissão e o usuário ativo são revalidados no banco a cada aviso; sessão expirada ou permissão retirada recarregam a página para o login.
- A página não tem menu nem dados do usuário logado. Rode a TV em modo quiosque e não use essa conta em outro lugar.

## Pendentes

G01 (unidades/serviços reais), H02/G02 (perfil de recepção e acesso do profissional ao paciente agendado — hoje não há concessão automática), H26 (escala/afastamento do profissional bloqueando agenda), lembretes por canal externo autorizado. Voz/som de chamada no painel não foi feito.
