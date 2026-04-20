# 📬 Assistente de Inbox Autônomo

Sistema em Python puro para ler, classificar e notificar sobre emails profissionais via Telegram — sem frameworks externos, custo zero de infraestrutura.

---

## 📁 Estrutura do Projeto

```
inbox-assistant/
│
├── main.py                  # Orquestrador principal
├── email_reader.py          # Conexão IMAP e extração de emails
├── ai_classifier.py         # Integração com Groq/Gemini + regras de negócio
├── telegram_notifier.py     # Formatação e envio do relatório
│
└── .github/
    └── workflows/
        └── inbox_assistant.yml   # Agendamento via GitHub Actions (cron 4h)
```

---

## ⚙️ Configuração Passo a Passo

### 1. Fork / Clone este repositório

```bash
git clone https://github.com/seu-usuario/inbox-assistant.git
cd inbox-assistant
```

### 2. Configure as variáveis de ambiente (Secrets do GitHub)

Vá em **Settings → Secrets and variables → Actions → New repository secret** e adicione:

| Secret               | Descrição                                              | Obrigatório |
|----------------------|--------------------------------------------------------|-------------|
| `IMAP_SERVER`        | Servidor IMAP (ex: `imap.gmail.com`)                  | ✅           |
| `EMAIL_ADDRESS`      | Seu endereço de email                                  | ✅           |
| `EMAIL_PASSWORD`     | Senha ou App Password                                  | ✅           |
| `TELEGRAM_BOT_TOKEN` | Token do bot (via [@BotFather](https://t.me/BotFather)) | ✅        |
| `TELEGRAM_CHAT_ID`   | Seu Chat ID (via [@userinfobot](https://t.me/userinfobot)) | ✅      |
| `GROQ_API_KEY`       | Chave da [Groq Cloud](https://console.groq.com)       | ✅ (ou Gemini) |
| `GEMINI_API_KEY`     | Chave do [Google AI Studio](https://aistudio.google.com) | ✅ (ou Groq) |

### 3. Gmail: use App Password (obrigatório)

O Gmail **bloqueia senhas comuns** para apps externos. Você precisa de uma **App Password**:

1. Ative a verificação em duas etapas: [myaccount.google.com/security](https://myaccount.google.com/security)
2. Acesse: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Crie uma senha para "Outro (nome personalizado)" → use como `EMAIL_PASSWORD`

### 4. Criar o Bot do Telegram

1. Fale com [@BotFather](https://t.me/BotFather) → `/newbot`
2. Siga as instruções e guarde o **token**
3. Fale com [@userinfobot](https://t.me/userinfobot) para obter seu **Chat ID**
4. Inicie uma conversa com seu bot (obrigatório para receber mensagens)

### 5. Obter API Keys gratuitas

**Groq (recomendado — mais rápido):**
- Cadastre em [console.groq.com](https://console.groq.com)
- Crie uma API Key — plano gratuito inclui ~14.400 req/dia

**Google Gemini (alternativa):**
- Acesse [aistudio.google.com](https://aistudio.google.com/app/apikey)
- Gere uma API Key — Gemini 1.5 Flash é gratuito

---

## 🚀 Executar Localmente (Testes)

```bash
# Copie e configure o arquivo de variáveis
cp .env.example .env
# Edite .env com suas credenciais

# Carregue as variáveis e execute
export $(cat .env | xargs) && python main.py
```

Arquivo `.env.example`:
```
IMAP_SERVER=imap.gmail.com
EMAIL_ADDRESS=seu@gmail.com
EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFxxxxxxxx
TELEGRAM_CHAT_ID=123456789
GROQ_API_KEY=gsk_xxxxxxxxxx
GEMINI_API_KEY=
HOURS_BACK=4
MAX_EMAILS=50
MAILBOX=INBOX
```

---

## 📊 Exemplo de Relatório no Telegram

```
📬 Relatório de Inbox — 20/04/2025 às 08:00h UTC
📊 5 email(s) novo(s):
  ✅ Profissional_Positivo: 1
  🚀 Profissional_Oportunidade: 1
  👤 Pessoal: 1
  ❌ Profissional_Negativo: 1
  🗑️ Spam: 1
──────────────────────────────

✅ [Profissional_Positivo] ⭐ DESTAQUE
📌 Assunto: Parabéns! Você passou para a próxima fase
👤 De: Recrutadora da Empresa X
📝 A empresa confirma aprovação na triagem de currículos e convida para entrevista técnica na próxima semana.

🚀 [Profissional_Oportunidade] ⭐ DESTAQUE
📌 Assunto: Vaga: Estágio em Segurança da Informação - Empresa Y
👤 De: RH da Empresa Y (LinkedIn Jobs)
📝 Vaga de estágio em Segurança da Informação para estudantes de Ciência da Computação. Foco em análise de vulnerabilidades e pentest.

...
🗑️ 1 email(s) de spam ignorados.
```

---

## 🏗️ Arquitetura

```
GitHub Actions (cron: a cada 4h)
         │
         ▼
      main.py
    ┌────────────────────────────────────────────┐
    │  1. fetch_unread_emails()  → email_reader  │
    │     └─ IMAP SSL → busca UNSEEN últimas 4h  │
    │                                            │
    │  2. classify_emails_batch() → ai_classifier│
    │     └─ Groq (Llama 3) ou Gemini Flash      │
    │        └─ Retorna JSON: categoria + resumo │
    │                                            │
    │  3. send_report() → telegram_notifier      │
    │     └─ Bot API → mensagem HTML formatada   │
    └────────────────────────────────────────────┘
```

---

## 🔧 Variáveis Opcionais

| Variável     | Padrão   | Descrição                                    |
|--------------|----------|----------------------------------------------|
| `HOURS_BACK` | `4`      | Janela de tempo para buscar emails           |
| `MAX_EMAILS` | `50`     | Limite máximo de emails por execução         |
| `MAILBOX`    | `INBOX`  | Caixa de entrada IMAP (ex: `[Gmail]/Spam`)   |

---

## 📦 Dependências

**Zero dependências externas.** Usa apenas bibliotecas nativas do Python 3.10+:
- `imaplib` — conexão IMAP
- `email` — parsing de mensagens
- `urllib` — requisições HTTP
- `json`, `logging`, `os`, `sys`, `re`, `time`, `datetime`

---

## 📝 Licença

MIT — use, modifique e distribua livremente.
