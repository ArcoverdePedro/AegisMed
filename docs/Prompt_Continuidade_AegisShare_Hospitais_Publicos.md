# Prompt de refatoração — AegisShare para hospital municipal de pequeno porte no SUS

Versão: 30/10/2026. Repositório: https://github.com/ArcoverdePedro/AegisShare

Uso: entregue este documento ao agente de desenvolvimento com acesso ao repositório. As instruções abaixo orientam implementação e preparação para homologação; não constituem parecer jurídico, certificação ou autorização para atendimento real.

## 1. Missão e resultado esperado

Atue como responsável pela evolução técnica do AegisShare, com experiência em Django, sistemas hospitalares, segurança, interoperabilidade SUS e requisitos brasileiros de prontuário eletrônico. Implemente as mudanças elegíveis, execute testes e produza evidências para os responsáveis institucionais.

Direcione o produto a um hospital geral municipal de pequeno porte, com foco em ambulatório e internação clínica de adultos. Entregue primeiro o ambulatório e, em uma segunda liberação independente, a internação clínica. Reduza alterações estruturais, reaproveite o código existente e conclua jornadas completas.

Trabalhe em incrementos revisáveis. Continue implementando enquanto houver tarefas elegíveis. Não encerre apenas com diagnóstico, documentação ou sugestões. Uma dependência externa deve bloquear somente as partes que realmente dependem dela.

O objetivo é atender aos requisitos legais aplicáveis ao hospital, à versão e aos serviços escolhidos, com controles e evidências verificáveis. Não prometa conformidade universal, segurança absoluta ou aprovação por órgãos públicos.

## 2. Escopo de produto já definido pelo usuário

Registre em G01, sem pedir novamente confirmação destas escolhas, a decisão de produto:

| Aspecto | Diretriz para desenvolvimento |
| --- | --- |
| Público prioritário | Hospital geral municipal de pequeno porte, com atendimento SUS. |
| Instituições | Uma instituição por instalação, com unidades e setores internos. |
| Primeira liberação | Ambulatório de adultos: cadastro, agenda, recepção, atendimento, prontuário, documentos, prescrição do recorte aprovado, pedidos/resultados e retorno. |
| Segunda liberação | Internação clínica adulta: leitos, admissão, transferência, prescrição, farmácia, enfermagem, materiais, alta e produção SUS. |
| Diagnóstico | Fluxos delimitados, próprios ou contratados, aproveitando pedidos, resultados e laudos existentes. |
| Administração | Farmácia, almoxarifado, compras e produção necessárias ao recorte; integração com sistemas administrativos existentes quando adequada. |
| Implantação | Docker Compose, armazenamento privado e documentação de instalação e recuperação. |
| Evolução futura | Outros serviços somente após fechar o recorte inicial e suas dependências. |

Use 5 a 30 leitos apenas como referência de dimensão da política federal específica de HPP. Isso não define universalmente o porte dos hospitais nem comprova simplicidade operacional. Não imponha essa faixa como restrição no banco ou limite artificial de licença.

Ficam fora das duas primeiras liberações: UTI, obstetrícia/maternidade, neonatologia, pediatria, centro cirúrgico/anestesia/CME, pronto-socorro com porta aberta, oncologia de alta complexidade, diálise, transplantes, hemoterapia própria e gestão de vários hospitais na mesma instância. Hospital-dia não é o regime inicial escolhido.

Essas exclusões delimitam a entrega do software. Não justificam apagar módulos, dados ou histórico; negar assistência; ou ignorar serviços existentes no hospital. Escolha uma instituição compatível ou formalize um piloto setorial integrado aos sistemas responsáveis pelas demais áreas, com continuidade de informação e responsabilidades claras.

A escolha acima não equivale à aprovação de um hospital real. Instituição, CNES, setores, serviços efetivos, capacidade, interfaces, protocolos, metas e responsáveis ainda precisam de validação institucional. Sem hospital indicado, desenvolva com hipóteses documentadas e dados sintéticos.

## 3. Retome o trabalho existente e preserve as entregas

1. Leia AGENTS.md e instruções aplicáveis, README, SECURITY.md, dependências, configurações, migrations, CI e testes.
2. Reutilize `docs/AEGISSHARE_PLANO_EXECUCAO_IA.md`, `docs/his/PROGRESSO.md`, `docs/his/DECISOES.md`, `docs/his/INVENTARIO_DADOS.md`, specs e ADRs. Atualize o plano existente; não mantenha um roteiro concorrente.
3. Confira branches, commits, estado do checkout e mudanças locais. Não use hashes, contagens de testes ou estados históricos como prova da versão atual. Preserve alterações e não faça reset, force-push ou integração destrutiva.
4. Identifique, por fluxo real, o que está implementado, incompleto, bloqueado ou obsoleto. Confira prontuário, agenda, ADT, farmácia, enfermagem, estoque, compras, laboratório, imagem, contas e backup antes de criar algo novo.
5. Reproduza a baseline da CI. Corrija regressões e registre comandos, ambiente, commit e resultado. Diferencie falha de código de limitação do ambiente.
6. Separe falta de configuração, regra institucional, funcionalidade, integração e problema estrutural. Refatore somente quando houver motivo demonstrado.

Atualize G01 como decisão de produto do usuário, com esta data, sem inventar aceite clínico ou jurídico. Reavalie os demais gates com alternativas e impacto. Não renomeie um bloqueio para declarar um cartão concluído.

## 4. Arquitetura e economia de mudanças

- Preserve o monólito Django, PostgreSQL, Forms, ORM, templates e Python; prefira function-based views e JavaScript apenas quando necessário à interação.
- Reutilize `Patient`, `Encounter`, usuários, permissões, auditoria, arquivos, leitos, prescrições e estoques canônicos. Evite cadastros paralelos e serviços genéricos sem uso concreto.
- Preserve a fronteira arquitetural existente, sem acrescentar APIs REST públicas. Integrações de saída e entradas autorizadas devem usar adaptadores delimitados, respeitando os contratos do projeto.
- Não introduza SPA, microsserviços, Kubernetes, filas distribuídas, novo framework de permissões ou nova camada de persistência sem necessidade comprovada.
- Mantenha módulos fora do recorte preservados e sem ampliação. Controle a ativação dos serviços no servidor, nas permissões e nos pontos de entrada; esconder menus é insuficiente. Reutilize mecanismos existentes antes de criar configuração nova.
- Use transações, constraints, bloqueios e idempotência nas disputas por agenda, leito, lote, saldo, dose, consumo, conta e processamento externo.
- Preserve autoria, histórico e versões. Correções clínicas devem ser rastreáveis, sem sobrescrever o fato anterior silenciosamente.
- Faça migrations compatíveis e ensaie a atualização com dados legados sintéticos. Não descarte tabelas ou registros para simplificar o piloto.
- Mantenha uma instalação por instituição. Workspaces de documentos não comprovam isolamento clínico entre hospitais.

## 5. Sequência obrigatória de implementação

### Etapa 0 — Base comum

Estabilize a baseline, confirme o escopo, corrija falhas relevantes de autorização/privacidade e prepare a matriz normativa. Feche os controles transversais necessários à primeira liberação, incluindo armazenamento, auditoria, autenticação, assinatura aplicável e restauração.

Trabalhe na matriz junto com as entregas. Não substitua implementação por documentação extensa. Escolhas técnicas reversíveis podem avançar sem hospital indicado, desde que não inventem protocolos clínicos ou aprovações.

### Etapa 1 — Ambulatório

Conclua identificação → agenda → recepção → atendimento → registros/documentos e prescrição incluída → pedidos/resultados → encerramento → retorno, com produção SUS e integrações aplicáveis ao recorte.

A primeira liberação deve ser utilizável por si. Se depender de farmácia, diagnóstico, assinatura ou outro serviço, entregue a dependência ou integre um fluxo institucional validado. Não marque dependência obrigatória como futura apenas para liberar o ambulatório.

### Etapa 2 — Internação clínica adulta

Conclua admissão → leito → avaliação e cuidados → prescrição → revisão/dispensação → administração ou exceção → transferência quando necessária → alta clínica/operacional → higienização → produção SUS e conciliação.

A liberação do ambulatório não autoriza a internação. Mantenha estados de validação e configurações independentes por serviço. Pendências exclusivas da internação não devem paralisar uma entrega ambulatorial que realmente as dispense.

## 6. Cadastro, prontuário e ambulatório

Implemente e valide:

- Identificação com nome social, múltiplos identificadores e origens, homônimos, representantes e responsáveis quando pertinentes; paciente desconhecido, identificação provisória e regularização auditada.
- Conciliação de duplicidades com análise autorizada, preservação de vínculos e possibilidade de correção rastreável. Não mescle pessoas apenas por coincidência de nome ou data de nascimento.
- Ausência de CPF, CNS, documento ou endereço fixo sem bloqueio indevido da assistência. Diferencie identificador local provisório de identificador emitido pelo CadSUS; nunca fabrique CPF/CNS ou declare cadastro oficial sem confirmação.
- Agenda por profissional/unidade, duração e disponibilidade aprovadas; reagendamento, cancelamento, falta, chegada, atendimento e retorno, com proteção contra concorrência e acesso indevido.
- Prontuário longitudinal com antecedentes, alergias/intolerâncias, problemas/diagnósticos, avaliação, plano, evolução multiprofissional e reconciliação medicamentosa necessários ao serviço.
- Vínculo consistente de registros, pedidos, documentos, resultados e prescrições ao paciente e ao encontro corretos; prevenção de edição em encontro encerrado fora do procedimento autorizado.
- Documentos com conteúdo/versionamento, autor, identificação profissional, instituição e datas pertinentes. Atestados e receitas externas exigem tratamento próprio de assinatura e finalidade.
- Encerramento, orientações, encaminhamento e retorno sem perda de pendências diagnósticas. Defina responsáveis pelo acompanhamento e comunicação de resultados conforme política clínica.

Reconfira a Portaria GM/MS nº 12.263/2026 e alterações posteriores para o CadSUS. Respeite as origens e restrições de alteração dos dados recebidos por interoperabilidade; não replique indiscriminadamente todos os campos do cadastro nacional no cadastro local.

Use terminologias e catálogos aprovados, com origem, versão e licença. Não amplie a coleta de dados sensíveis sem finalidade definida.

## 7. Prescrição, diagnóstico e limites clínicos

Reutilize a prescrição estruturada e a revisão farmacêutica existentes. Complete os fluxos necessários a cada liberação, incluindo alergias estruturadas e seus estados de conhecimento, medicamentos em uso, suspensão, substituição e reconciliação.

Não interprete ausência de informação como ausência de alergia. Quando faltarem dados, referência ou avaliação elegível, mostre indisponibilidade explícita da checagem; não produza confirmação fictícia de segurança. Não invente doses, interações, valores críticos, classificações ou protocolos. Conteúdo clínico depende de fonte aprovada e governança profissional.

Prescrições ambulatoriais externas e ordens internas de medicação devem ter estados e requisitos adequados às suas finalidades. Para receitas de controle especial ou sujeitas à retenção, confira as normas sanitárias, modelos, numeração, assinatura e integração ao SNCR aplicáveis. A RDC Anvisa nº 1.000/2025, a RDC nº 1.028/2026 e alterações posteriores precisam ser reconferidas na execução. Assinatura ICP-Brasil isolada não comprova o cumprimento de todas essas exigências.

Não habilite modalidade de receita eletrônica sem cumprir seus requisitos. Quando a instituição usar um procedimento físico ou serviço externo válido, documente o fluxo, a fonte de verdade e a reconciliação; não apresente impressão, imagem de assinatura ou documento digitalizado como equivalente automático ao receituário eletrônico regulamentado. Se a modalidade for indispensável ao recorte, sua ausência bloqueia a liberação correspondente.

A Anvisa publicou em 29/10/2026 notícia sobre prorrogação da transição do SNCR. Verifique o ato publicado, vigência e categorias alcançadas antes de fixar qualquer prazo; não copie um calendário desatualizado para o código.

Para diagnóstico, aproveite pedidos, amostras, resultados manuais e laudos versionados existentes. Complete, conforme serviço, coleta, recebimento, rejeição/recoleta, validação, liberação, retificação e acesso autorizado. Diferencie resultado interno validado de documento recebido de prestador externo, preservando origem e responsabilidade.

Não obrigue desenvolver analisadores, PACS/DICOM ou laudos automatizados para um recorte que possa operar com uma integração ou procedimento manual institucionalmente validado. Também não dispense integração indispensável ao funcionamento real do serviço.

Avalie a finalidade pretendida de cálculos, alertas e apoio à decisão perante a regulamentação de software como dispositivo médico. Não presuma que o HIS inteiro é automaticamente regulado ou isento; gratuidade e código aberto não definem esse enquadramento. Não acrescente diagnóstico ou prescrição autônoma por IA.

## 8. Internação, enfermagem, farmácia e materiais

Antes da segunda liberação, conclua:

1. Admissão e ocupação exclusivas, reserva quando necessária, transferência, bloqueio, higienização, isolamento e disponibilização de leitos conforme política operacional aprovada.
2. Reconciliação e coerência entre alta clínica, encerramento do encontro, liberação operacional do leito, prescrições e pendências. Evite alta duplicada ou administração após encerramento indevido.
3. Processo de Enfermagem e registros compatíveis com a categoria profissional: avaliação, diagnósticos, planejamento, implementação e evolução conforme atribuições e política aprovada. Sinais vitais e administração isolados não completam esse processo.
4. Cuidados planejados e realizados, dispositivos, balanço hídrico e passagem de plantão necessários à enfermaria.
5. Aprazamento e dose prevista ligados à prescrição vigente; revisão, dispensação e administração ou exceção identificadas por paciente, profissional, horário, medicamento e lote pertinente.
6. Recusa, omissão, atraso, administração parcial, divergência e correção com motivo; prevenção de duplicidade e de administração incompatível com suspensão ou alteração da ordem.
7. Recebimento, armazenamento, validade, bloqueio de lote, dispensação, devolução e estorno conciliados; quantidades e conversões aprovadas. Evite estoque negativo e conversões presumidas.
8. Consumo de materiais por paciente quando necessário, requisições e compras compatíveis com o fluxo local, com segregação de responsabilidades e trilha de auditoria.
9. Cadastro profissional, vínculo, credenciais, afastamentos e escalas estritamente necessários à autorização e operação dos serviços.

Mantenha administração e dispensação online. Não amplie o piloto offline existente para medicação, ADT ou estoque. No offline previamente aprovado, preserve cifra, revalidação na sincronização, conflitos explícitos e limpeza no logout.

## 9. Produção SUS e interoperabilidade

Trate a produção SUS como parte da entrega e mantenha vínculo verificável com o fato assistencial. Não confunda conta manual ou faturamento particular com produção pública.

- Mapeie CNES, profissionais/CBO, procedimentos e SIGTAP por competência, com procedência e versão.
- Para o ambulatório, implemente ou integre os instrumentos SIA/BPA/APAC efetivamente aplicáveis; APAC não é requisito universal de toda consulta.
- Para a internação, implemente ou integre SIH/AIH conforme o serviço, o gestor e os contratos oficiais vigentes.
- Cubra autorização quando exigida, consistências, fechamento, correção, rejeição, retorno, reprocessamento e conciliação. Evite produção duplicada e preserve competências já enviadas.
- Se o gestor já utilizar software de produção, prefira integração delimitada com fonte de verdade definida a reescrever um ERP. O processo externo precisa ter responsável, rastreabilidade e evidência de funcionamento.
- Gerar arquivo não significa transmitir, processar ou obter aceite. Registre esses estados separadamente e trate resposta perdida, timeout e duplicidade sem falso sucesso.
- Para RNDS, CadSUS, regulação e sistemas municipais/estaduais, confirme modelos, versões, obrigações, contratos e credenciais aplicáveis. Não presuma um único sistema de regulação em todo o Brasil.
- Use os modelos oficiais pertinentes ao ambulatório e à alta clínica. FHIR genérico ou exportação mínima de `Patient` não comprovam integração RNDS nem exportação completa do prontuário.
- Observe o Decreto nº 12.560/2025 e normas complementares. Para compartilhamentos abrangidos pelo seu art. 2º, § 1º, inclua o RIPD prévio exigido, sob responsabilidade institucional.
- Sem credenciais autorizadas, entregue adaptadores, contratos, testes e pendências explícitas, mantendo a ativação real bloqueada.

Implemente persistência de estado, correlação, idempotência, retries limitados, quarentena e reprocessamento auditável com os recursos já disponíveis. Não introduza infraestrutura distribuída sem necessidade demonstrada.

## 10. Matriz de requisitos brasileiros e aplicabilidade

Crie ou atualize uma matriz concisa com: requisito, fonte oficial e dispositivo, vigência/data da consulta, âmbito, obrigação ou referência técnica, controle implementado, procedimento institucional, evidência/teste, responsável e pendência.

Consulte fontes primárias atualizadas. Diferencie obrigação legal, norma profissional/sanitária, exigência contratual, política institucional e escolha de engenharia. Não rotule todos os controles deste prompt como imposições textuais da lei.

Cubra pelo menos:

| Tema | Trabalho exigido para este produto |
| --- | --- |
| SUS e identificação | Verificar Lei nº 8.080/1990, CadSUS vigente e regras dos serviços. Preservar acesso e histórico nas regularizações. |
| LGPD e Poder Público | Mapear finalidades e bases legais por operação, dados sensíveis, compartilhamentos, direitos e responsabilidades. Não adotar consentimento genérico como fundamento de todo atendimento SUS. |
| Guarda de prontuários | Aplicar Lei nº 13.787/2018, normas profissionais e arquivísticas pertinentes. Preservar autenticidade, integridade, confidencialidade e rastreabilidade. |
| Assinaturas | Mapear Lei nº 14.063/2020, ICP-Brasil/ITI e normas profissionais/sanitárias por documento, finalidade e contexto. |
| Medicina | Verificar regras vigentes do CFM sobre prontuários, sigilo e documentos, incluindo a Resolução nº 1.821/2007 e suas alterações, sem aplicar dispositivo revogado. |
| Enfermagem | Verificar Resoluções Cofen nº 736/2024 e nº 754/2024 e sucessoras, para Processo de Enfermagem, registros, acesso e prontuário eletrônico. |
| Receituários | Verificar regras Anvisa/SNCR vigentes e a diferença entre ordens internas, receitas externas, documentos físicos e eletrônicos. |
| SaMD | Avaliar cada função clínica e finalidade pretendida perante RDC nº 657/2022 e regulamentos pertinentes/sucessores. |
| RNDS e produção | Verificar Decreto nº 12.560/2025, modelos oficiais, competências e requisitos dos instrumentos SUS utilizados. |
| Adoção e contratação | Identificar a natureza jurídica do operador e o regime pertinente. Lei nº 14.133/2021 e Lei nº 13.303/2016 têm âmbitos diferentes; gratuidade não dispensa automaticamente procedimentos de adoção/contratação. |
| Acessibilidade | Verificar Lei nº 13.146/2015 e regras do ente. Registrar referenciais de avaliação escolhidos, como WCAG/eMAG, distinguindo referência técnica de obrigação aplicável. |
| Segurança do paciente e vigilância | Verificar normas sanitárias e rotinas de notificação compulsória aplicáveis aos serviços. Definir o que o sistema registra, transmite ou encaminha ao responsável, com contingência. |
| Licença e dependências | Preservar a licença existente, avisos e obrigações de disponibilização do código correspondente quando incidentes; verificar licenças dos catálogos e dependências. |

Retenção: confronte o art. 6º e seus parágrafos da Lei nº 13.787/2018, normas profissionais, regras arquivísticas, valor histórico e impedimentos legais. Não implemente expurgo automático por completar 20 anos. Diferencie documentos digitalizados e originalmente eletrônicos, sem ignorar a extensão prevista no § 5º. Descarte depende do procedimento e das autoridades competentes.

Assinaturas: documente a relação dos arts. 13 e 14 da Lei nº 14.063/2020 com a exceção relativa aos atos internos hospitalares e com as normas profissionais específicas. Essa exceção não elimina os demais deveres de autoria, integridade e registro. Para prontuário integralmente digital de Enfermagem, avalie expressamente a exigência de assinatura qualificada prevista no art. 2º, § 1º, da Resolução Cofen nº 754/2024, e suas atualizações. Não declare login/senha suficiente para operação sem papel.

Distinga atendimento a requisitos S-RES, exigência de contrato e certificação efetivamente obtida. Não apresente checklist interno ou uso de biblioteca como certificação SBIS, aprovação do CFM ou regularização Anvisa.

Se houver dúvida de enquadramento ou conflito normativo, registre a questão concreta e prepare evidências para avaliação competente. Avance nas partes independentes; não invente uma interpretação jurídica para remover um bloqueio.

## 11. Proteção de dados, acesso e assinatura técnica

Implemente como critérios de engenharia do produto, relacionando-os à matriz quando houver fundamento específico:

- Matriz de acesso por função, unidade, equipe, vínculo e paciente; autorizações no servidor em listas, buscas, detalhes, POSTs, arquivos, exportações, Channels e sincronização.
- Separação entre administração técnica e acesso assistencial. Contas privilegiadas não devem receber acesso clínico indiscriminado por conveniência.
- Negação por padrão, revalidação após revogação, proteção contra formulário antigo e acesso emergencial temporário, justificado e revisável conforme política aprovada.
- Contas individuais, MFA para privilégios elevados e conforme risco assistencial, revogação de sessões e gestão segura de credenciais.
- Auditoria de leitura e alteração com contexto suficiente, sem copiar conteúdo clínico desnecessário; segregação de privilégios e proteção verificável do histórico. Append-only no Django não torna o banco inviolável.
- HTTPS, cookies seguros, configuração de hosts/origens, segredos protegidos e banco/Redis sem exposição desnecessária.
- Arquivos privados cifrados, downloads autorizados, backups cifrados e proteção de volumes. Defina proteção do banco conforme risco e ambiente; cifra de arquivos não significa cifra de todo o banco.
- Prevenção de dados clínicos em logs, telemetria, mensagens, notificações, URLs e caches indevidos; relatórios agregados com avaliação de risco de reidentificação.
- Exportação íntegra e legível do prontuário com autoria, versões, documentos, referências e evidências pertinentes, além de formato estruturado quando necessário. Avalie vazamento por exportações.
- Inventário do tratamento, responsáveis reais, fornecedores, direitos dos titulares, representantes, retenção e incidentes. Encerrar um protocolo não comprova atendimento do direito.

Prepare resposta a incidentes com contenção, preservação de evidências, análise de risco e encaminhamento ao controlador. Reconfira os prazos e critérios da Resolução CD/ANPD nº 15/2024 e alterações; não automatize comunicações externas sem atuação dos responsáveis autorizados.

Não atribua automaticamente ao mantenedor do repositório os papéis de controlador ou encarregado. Avalie subprocessadores e transferências internacionais antes de habilitar compartilhamentos; não presuma uma obrigação geral de hospedar todos os dados no Brasil.

Para assinatura, preserve exatamente conteúdo e versão assinados, identidade profissional, evidências, verificação e tratamento de expiração/revogação/indisponibilidade conforme o padrão aplicável. Hash, login, TOTP, nome digitado e revisão farmacêutica não substituem automaticamente assinatura avançada ou qualificada. Reutilize padrões e bibliotecas adequados; não crie criptografia própria nem armazene chaves privadas de profissionais sem arquitetura aprovada.

## 12. Operação portátil e recuperável

- Mantenha Docker Compose como instalação principal, com configurações documentadas e valores de exemplo sem segredos reais. Preserve suporte a banco e serviços externos quando existente.
- Faça o núcleo operar com armazenamento privado próprio, sem obrigatoriedade de Pinata/IPFS ou de serviço comercial. Migrações de arquivos devem verificar integridade e capacidade de recuperação.
- Separe desenvolvimento, homologação e produção. Use dados sintéticos; não envie bases reais, prontuários ou segredos a ferramentas de IA ou terceiros.
- Faça persistência e backup respeitarem a configuração real, inclusive `FILE_STORAGE_ROOT`, se existente. Teste caminho alternativo para detectar diretórios fixos divergentes.
- Automatize backup de banco, arquivos e metadados necessários; cifra, retenção, cópia externa, alertas e recuperação das chaves devem ter procedimentos claros.
- Teste restauração integral, decifragem, vínculos e continuidade das operações. Não substitua `FILE_ENCRYPTION_KEY` sem procedimento seguro de rotação/reempacotamento.
- Defina RPO/RTO com a instituição. Meça recuperação e desempenho com massa/concorrência representativas e registre ambiente, percentis, limites e gargalos.
- Prepare atualização, migrations coordenadas, reversão de código compatível, certificados, health checks e falhas de dependências. Reverter código não significa reverter dados com segurança.
- Documente contingência assistencial e reconciliação posterior; use rotinas existentes sempre que possível. Não confirme operações que falharam por indisponibilidade.
- Mantenha inventário de dependências/SBOM, atualização, canal privado de reporte e revisão de segurança antes do primeiro uso real.

## 13. Testes e critérios de liberação

Execute os checks disponíveis no checkout atual: Django/PostgreSQL, migrations, lint, concorrência, Compose, Playwright, acessibilidade e privacidade pertinentes. Associe evidências ao commit e ao ambiente. Testes simulados não comprovam homologação com sistemas reais.

Antes de liberar o ambulatório, demonstre:

1. Cadastro sem documentos → identificação provisória local → regularização → histórico preservado.
2. Agenda → chegada → consulta → prontuário/documentos → prescrição incluída → encerramento → retorno.
3. Pedido → execução própria ou encaminhamento externo → resultado autorizado → acompanhamento → retificação rastreável.
4. Documento assinado → verificação → correção por nova versão, sem invalidação silenciosa da anterior.
5. Produção ambulatorial aplicável → validação → envio ou integração institucional → retorno → correção e conciliação.
6. Revogação com formulário aberto, acesso cruzado entre pacientes/setores, downloads e exportações negados corretamente.
7. Instalação limpa → atualização com legados → backup → restauração e decifragem → retomada.

Antes de liberar a internação, acrescente:

1. Duas admissões concorrentes disputando o mesmo leito, sem dupla ocupação.
2. Internação → cuidados → transferência → alta clínica/operacional → higienização → disponibilidade.
3. Prescrição → revisão → dispensação → administração ou exceção → devolução/estorno conciliado.
4. Suspensão/alteração da ordem, troca de plantão e encerramento concorrente, sem dose duplicada ou registro incompatível.
5. Material recebido → estoque → consumo por paciente → correção → saldo conciliado.
6. Produção hospitalar aplicável → processamento/retorno → rejeição/correção → conciliação.
7. Resposta de rede perdida após commit e repetição da operação, sem duplicação de dose, saldo, movimento ou produção.

Em ambas as liberações, verifique teclado, leitor de tela, contraste, telas usuais, proteção de dados locais e papéis profissionais reais. Testes devem cobrir regras e riscos concretos; não crie testes que apenas reproduzam a implementação.

Classifique cada serviço como: implementado; tecnicamente validado; homologação institucional pendente; ou aprovado para hospital/versão/configuração identificados. Não declare aprovação por existir código ou testes verdes. Não use N/A para requisito obrigatório do recorte.

A utilização real exige revisão de riscos, jornadas aprovadas, treinamento, responsáveis operacionais, contingência testada, requisitos legais aplicáveis atendidos e aceites clínico, técnico, administrativo e jurídico pertinentes. Bloqueio obrigatório do serviço impede sua liberação, mas não necessariamente a de outro serviço independente.

## 14. Entregáveis e continuidade

Atualize os documentos existentes e acrescente somente o necessário:

- Escopo de cada liberação e mapa de reaproveitamento/alterações.
- Matriz normativa e de responsabilidades, com evidências e pendências.
- Matriz de acesso e inventário de tratamento atualizados.
- Guia de instalação, atualização, backup, restauração e contingência.
- Manual curto por perfil e roteiros de homologação do ambulatório e da internação.
- Notas de versão, limitações conhecidas e evidências dos testes.
- Subsídios/minutas de adoção, suporte, tratamento de dados e RIPD pertinente, sujeitos à revisão institucional.

Não duplique documentos equivalentes. Preserve IDs Hxx/Gxx e rastreabilidade das specs. Registre decisões necessárias com pergunta objetiva, alternativas, responsável e impacto, sem exigir validação institucional para escolhas técnicas rotineiras.

Comece agora: confira o checkout e a baseline, registre o recorte de G01, escolha a próxima lacuna elegível do ambulatório e implemente-a com testes. Continue na tarefa seguinte até concluir o que puder avançar com as autorizações e informações disponíveis.

Se todas as tarefas restantes exigirem decisão externa, entregue o pacote revisável e as perguntas exatas para desbloqueio. Não invente autorização, conteúdo clínico, credenciais ou pareceres. Mantenha checkpoint curto para retomada.

Este prompt autoriza desenvolvimento e validação em ambiente adequado com dados sintéticos. Não autoriza alterar produção, atender pacientes reais, ativar integrações reais, enviar dados a terceiros ou publicar mudanças remotamente sem autorização correspondente. Prepare alterações e commits locais revisáveis, respeitando o fluxo autorizado do repositório.

Ao final de cada incremento, informe: comportamento entregue; código/commit; verificações executadas e resultados; limitações; decisões externas indispensáveis; próxima tarefa executável. Não encerre enquanto houver implementação elegível.

## 15. Fontes oficiais para a matriz e reconferência

Fontes consultadas ou pontos de partida oficiais. Reconfira os textos consolidados, atos posteriores, vigência, âmbito e publicação oficial na execução. A existência de uma página institucional não substitui o dispositivo aplicável.

1. [Ministério da Saúde — Política para Hospitais de Pequeno Porte](https://www.gov.br/saude/pt-br/composicao/saes/dahu/atencao-hospitalar/politica-nacional-para-os-hpp).
2. [Lei nº 8.080/1990 — organização e funcionamento dos serviços de saúde](https://www.planalto.gov.br/ccivil_03/leis/l8080.htm).
3. [LGPD — Lei nº 13.709/2018, texto compilado](https://presidencia.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm).
4. [ANPD — guia para o tratamento de dados pelo Poder Público](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_orientativo_tratamento_de_dados_pessoais_pelo_poder_publico).
5. [Lei nº 13.787/2018 — prontuários](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13787.htm).
6. [Lei nº 14.063/2020 — assinaturas eletrônicas](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/lei/l14063.htm).
7. [CFM — Resolução nº 1.821/2007](https://sistemas.cfm.org.br/normas/arquivos/resolucoes/BR/2007/1821_2007.pdf) e [Resolução nº 2.218/2018](https://sistemas.cfm.org.br/normas/visualizar/resolucoes/br/2018/2218).
8. [Cofen — Resolução nº 736/2024, Processo de Enfermagem](https://www.cofen.gov.br/resolucao-cofen-no-736-de-17-de-janeiro-de-2024/).
9. [Cofen — Resolução nº 754/2024, prontuário eletrônico](https://www.cofen.gov.br/resolucao-cofen-no-754-de-16-de-maio-de-2024/).
10. [Portaria GM/MS nº 12.263/2026 — CadSUS](https://bvsms.saude.gov.br/bvs/saudelegis/gm/2026/prt12263_05_10_2026.html).
11. [Ministério da Saúde — sistemas de informação SUS, CNES, SIGTAP, SIA e SIH](https://www.gov.br/saude/pt-br/acesso-a-informacao/gestao-do-sus/programacao-regulacao-controle-e-financiamento-da-mac/sistemas-de-informacao-em-saude).
12. [Decreto nº 12.560/2025 — RNDS e Plataformas SUS Digital](https://presidencia.gov.br/ccivil_03/_ato2023-2026/2025/decreto/d12560.htm).
13. [Ministério da Saúde — legislação da RNDS e modelos de informação](https://www.gov.br/saude/pt-br/composicao/seidigi/rnds/legislacao) e [guia oficial](https://rnds-guia.saude.gov.br/).
14. [Anvisa — perguntas e respostas sobre software como dispositivo médico/RDC nº 657/2022](https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/produtos-para-a-saude/manuais/software-como-dispositivo-medico-perguntas-e-respostas).
15. [Anvisa — SNCR e orientações por perfil](https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/controlados/sncr).
16. [Anvisa — RDC nº 1.000/2025, receituários eletrônicos](https://anvisalegis.datalegis.net/action/ActionDatalegis.php?acao=abrirTextoAto&cod_menu=1696&cod_modulo=134&numeroAto=00001000&orgao=RDC%2FDC%2FANVISA%2FMS&pesquisa=true&seqAto=000&tipo=RDC&valorAno=2025).
17. [Anvisa — comunicado de 29/10/2026 sobre a transição do SNCR](https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2026/20a-reuniao-ordinaria-publica-da-anvisa-periodo-de-transicao-para-emissao-de-receitas-eletronicas-no-sncr-e-prorrogado). Conferir o ato normativo publicado e alterações posteriores.
18. [ANPD — comunicação de incidentes e Resolução nº 15/2024](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis).
19. [Lei nº 14.133/2021 — licitações e contratos](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm).
20. [Lei nº 13.303/2016 — empresas públicas e sociedades de economia mista](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2016/lei/l13303.htm).
21. [Lei nº 13.146/2015 — acessibilidade e inclusão](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm).
22. [SBIS — manuais e requisitos de certificação S-RES](https://sbis.org.br/certificacoes/certificacao-software/manuais-e-listas-de-requisitos/). Referência técnica/setorial; não é certificação já obtida pelo projeto.

Se uma fonte estiver indisponível ou não permitir confirmar vigência, procure outra publicação oficial, registre a limitação e não transforme uma referência histórica em requisito atual presumido.
