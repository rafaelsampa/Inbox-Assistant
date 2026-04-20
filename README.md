
### Assistente de Inbox Autônomo: Tech Stack

**1. Objetivo do Projeto**

Desenvolver um sistema autônomo em código puro para ler, classificar e notificar o usuário sobre emails recebidos em uma conta profissional. O sistema deve atuar como um filtro inteligente, consolidando as informações e enviando um relatório estruturado via Telegram a cada 4 horas. O projeto deve ter custo zero de infraestrutura e operação.

**2. Motivação e Filosofia Arquitetural**

O foco principal deste projeto é a estabilidade temporal, a performance e o controle absoluto do código. Plataformas "low-code" como o n8n frequentemente quebram fluxos de trabalho devido a atualizações de versão e mudanças de interface, gerando engessamento. Este projeto visa resgatar a base da automação (scripts diretos, execução via cron e integrações via API) para garantir um sistema resiliente, que funcione por mais tempo sem necessidade de manutenção constante. Serve também como um laboratório prático para aprofundamento em infraestrutura de software e consumo de APIs de LLMs.

**3. Stack Tecnológico**

* **Linguagem:** Python 3.x (uso estrito de bibliotecas nativas como `imaplib` e `email` para reduzir dependências externas).
* **Agendador:** GitHub Actions (execução programada via cron a cada 4 horas).
* **Notificação:** API nativa do Telegram (via requisições HTTP diretas para um bot gerenciado pelo BotFather).
* **Inteligência Artificial:** Groq Cloud API (modelos Llama 3) ou Google Gemini API, priorizando os planos gratuitos (Free Tier).

**4. Regras de Negócio e Prompting da IA**
A IA integrada ao script deve receber o corpo do email extraído e retornar um JSON estrito. As regras de classificação são:
* **[Pessoal]:** Identificar o remetente e a suposta identidade (exemplo: Colega de faculdade, familiar).
* **[Profissional] Positivo / Negativo:** Filtro focado exclusivamente em respostas de processos seletivos.
* **[Profissional] Oportunidade:** Alertas sobre novas vagas de estágio em Ciência da Computação. O filtro deve dar destaque especial para vagas em áreas técnicas como Segurança da Informação, Criptografia, Infraestrutura de Software ou Sistemas Operacionais.
* **[Spam]:** Lixo eletrônico, newsletters irrelevantes, promoções e comunicações genéricas de sistemas.

* **Conteúdo Extraído:** O relatório final deve conter um resumo direto do corpo do email, com limite máximo e inflexível de 100 palavras.

**5. Requisitos de Entrega (Instruções para a IA Desenvolvedora)**
* Fornecer o código em blocos modulares, separando a lógica de conexão de email, a formatação do prompt para a LLM e o envio da mensagem para o Telegram.
* Incluir tratamento de erros básico para evitar que o script quebre no GitHub Actions (exemplo: falha na conexão IMAP ou timeout na API da IA).
* O código final deve ser legível, comentado e focado na simplicidade.
