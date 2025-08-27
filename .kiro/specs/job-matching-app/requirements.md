# Requirements Document

## Introduction

Este documento define os requisitos para um aplicativo Python que utiliza análise de dados, web scraping e IA para buscar vagas de emprego compatíveis com o currículo do usuário. O sistema permitirá upload de currículos em LaTeX, análise por IA local (Ollama), web scraping de vagas, matching inteligente e adaptação automática de currículos para vagas específicas.

## Requirements

### Requirement 1

**User Story:** Como um usuário, eu quero fazer upload do meu currículo em formato LaTeX, para que o sistema possa analisá-lo e encontrar vagas compatíveis.

#### Acceptance Criteria

1. WHEN o usuário seleciona um arquivo LaTeX THEN o sistema SHALL aceitar e armazenar o arquivo
2. WHEN o arquivo é carregado THEN o sistema SHALL validar se é um arquivo LaTeX válido
3. WHEN o currículo é armazenado THEN o sistema SHALL permitir compilação para PDF a qualquer momento
4. IF o arquivo não for LaTeX válido THEN o sistema SHALL exibir mensagem de erro específica

### Requirement 2

**User Story:** Como um usuário, eu quero que a IA local analise meu currículo e extraia keywords relevantes, para que eu possa revisar e ajustar os termos de busca.

#### Acceptance Criteria

1. WHEN o currículo é processado THEN o sistema SHALL usar Ollama para extrair keywords importantes
2. WHEN as keywords são extraídas THEN o sistema SHALL exibi-las em interface editável
3. WHEN o usuário modifica keywords THEN o sistema SHALL permitir adicionar e remover termos
4. WHEN keywords são atualizadas THEN o sistema SHALL salvar as preferências do usuário

### Requirement 3

**User Story:** Como um usuário, eu quero visualizar vagas de emprego em páginas organizadas, para que eu possa navegar facilmente pelos resultados.

#### Acceptance Criteria

1. WHEN vagas são encontradas THEN o sistema SHALL exibir 30 vagas por página
2. WHEN a página carrega THEN o sistema SHALL mostrar listagem à esquerda com título e tags
3. WHEN uma vaga é exibida THEN o sistema SHALL mostrar tags para modalidade, nível, localização e tecnologias
4. WHEN há mais vagas THEN o sistema SHALL fornecer navegação entre páginas

### Requirement 4

**User Story:** Como um usuário, eu quero selecionar uma vaga e ver todos os detalhes, para que eu possa avaliar se é adequada para mim.

#### Acceptance Criteria

1. WHEN uma vaga é selecionada THEN o sistema SHALL exibir detalhes completos à direita
2. WHEN detalhes são mostrados THEN o sistema SHALL incluir descrição, empresa, site origem e links de candidatura
3. WHEN uma vaga está selecionada THEN o sistema SHALL manter a seleção visualmente destacada

### Requirement 5

**User Story:** Como um usuário, eu quero adaptar meu currículo para uma vaga específica, para que eu possa otimizar minhas chances no ATS.

#### Acceptance Criteria

1. WHEN o usuário clica em "adaptar currículo" THEN o sistema SHALL criar uma cópia do LaTeX original
2. WHEN a cópia é criada THEN o sistema SHALL enviar para IA local para adaptação
3. WHEN a adaptação é concluída THEN o sistema SHALL compilar para PDF e disponibilizar download
4. WHEN o processo termina THEN o sistema SHALL manter o arquivo original inalterado

### Requirement 6

**User Story:** Como um usuário, eu quero que o sistema faça web scraping de múltiplos sites de vagas, para que eu tenha acesso a um grande volume de oportunidades.

#### Acceptance Criteria

1. WHEN o sistema busca vagas THEN o sistema SHALL fazer scraping de múltiplos sites de emprego
2. WHEN dados são coletados THEN o sistema SHALL extrair informações estruturadas das vagas
3. WHEN scraping falha THEN o sistema SHALL continuar com outros sites e registrar erros
4. WHEN dados são obtidos THEN o sistema SHALL armazenar em banco de dados local

### Requirement 7

**User Story:** Como um usuário, eu quero que o sistema funcione com vagas em português e inglês, para que eu possa me candidatar a oportunidades internacionais.

#### Acceptance Criteria

1. WHEN IA processa texto THEN o sistema SHALL reconhecer português e inglês
2. WHEN keywords são extraídas THEN o sistema SHALL identificar termos em ambos idiomas
3. WHEN vagas são analisadas THEN o sistema SHALL processar descrições multilíngues
4. WHEN matching é feito THEN o sistema SHALL considerar equivalências entre idiomas

### Requirement 8

**User Story:** Como um usuário, eu quero que o sistema mantenha histórico de currículos e buscas, para que eu possa gerenciar múltiplas versões e consultas.

#### Acceptance Criteria

1. WHEN currículo é carregado THEN o sistema SHALL armazenar em banco de dados
2. WHEN buscas são realizadas THEN o sistema SHALL salvar histórico de consultas
3. WHEN usuário acessa histórico THEN o sistema SHALL exibir versões anteriores
4. WHEN dados são armazenados THEN o sistema SHALL manter integridade e backup

