### Ficha Técnica: Assistente de Inbox

**Tecnologias Base:**
* **Linguagem:** Python 3.x
* **Agendador:** GitHub Actions (permite rodar o script de graça na nuvem a cada 4 horas)
* **Mensageria:** API do Telegram (BotFather)
* **Leitura de Email:** Biblioteca nativa `imaplib` do Python

**Motor de Inteligência Artificial (Opções Gratuitas):**
* **Groq Cloud (Recomendado):** Oferece acesso via API aos modelos Llama 3. É extremamente rápido e tem um plano gratuito (Free Tier) perfeito para analisar textos curtos.
* **Google AI Studio (Gemini):** Oferece uma cota gratuita excelente para desenvolvedores.

**Regras de Negócio e Classificação:**
O prompt do sistema será configurado para retornar um JSON estruturado seguindo exatamente estas diretrizes de análise:

* **[Pessoal]** Nome do Remetente : Suposta Identidade (ex: Colega de faculdade, familiar)
* **[Profissional]** Positivo / Negativo : Filtro focado em respostas de processos seletivos.
* **[Profissional]** Oportunidade : Alertas sobre novas vagas, focando em posições de estágio em Ciência da Computação, especialmente em áreas de infraestrutura, segurança da informação ou criptografia.
* **[Spam]** : Lixo eletrônico, newsletters irrelevantes e promoções.

*Conteúdo Extraído:* Resumo do corpo do email limitado a um máximo de 100 palavras.
