"""
main.py
-------
Orquestrador principal do Assistente de Inbox Autônomo.
Este script é o ponto de entrada chamado pelo GitHub Actions a cada 4 horas.

Fluxo:
  1. Lê variáveis de ambiente
  2. Busca emails não lidos via IMAP (últimas 4h)
  3. Classifica cada email via LLM (Groq ou Gemini)
  4. Envia relatório estruturado via Telegram
  5. Encerra com exit code 0 (sucesso) ou 1 (falha crítica)
"""

import logging
import os
import sys
import traceback

from email_reader import fetch_unread_emails
from ai_classifier import classify_emails_batch
from telegram_notifier import send_report, send_error_alert

# ─── Configuração de logging ─────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("main")


def validate_env() -> bool:
    """Verifica se as variáveis de ambiente obrigatórias estão presentes."""
    required = [
        "IMAP_SERVER", "EMAIL_ADDRESS", "EMAIL_PASSWORD",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GEMINI_API_KEY"
    ]
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        logger.error(f"Variáveis ausentes: {', '.join(missing)}")
        return False
    return True


def main() -> int:
    """
    Ponto de entrada principal. Retorna 0 para sucesso, 1 para falha.
    """
    logger.info("═══════════════════════════════════════════")
    logger.info("   Assistente de Inbox Autônomo — Iniciando")
    logger.info("═══════════════════════════════════════════")

    # ── 1. Validação de ambiente ──────────────────────────────────────────────
    if not validate_env():
        send_error_alert("Variáveis de ambiente faltando. Verifique os Secrets do GitHub Actions.")
        return 1

    imap_server    = os.environ["IMAP_SERVER"]
    email_address  = os.environ["EMAIL_ADDRESS"]
    email_password = os.environ["EMAIL_PASSWORD"]
    hours_back     = int(os.getenv("HOURS_BACK", "4"))
    max_emails     = int(os.getenv("MAX_EMAILS", "50"))
    mailbox        = os.getenv("MAILBOX", "INBOX")

    try:
        # ── 2. Busca de emails ────────────────────────────────────────────────
        logger.info(f"Buscando emails das últimas {hours_back}h em '{mailbox}'...")
        emails = fetch_unread_emails(
            imap_server=imap_server,
            email_address=email_address,
            password=email_password,
            mailbox=mailbox,
            hours_back=hours_back,
            max_emails=max_emails,
        )
        logger.info(f"Total de emails para processar: {len(emails)}")

        # ── 3. Classificação via IA ───────────────────────────────────────────
        if emails:
            logger.info("Iniciando classificação via IA...")
            emails_classified = classify_emails_batch(emails)
        else:
            emails_classified = []

        # ── 4. Envio do relatório ─────────────────────────────────────────────
        logger.info("Enviando relatório via Telegram...")
        success = send_report(emails_classified)

        if success:
            logger.info("✅ Relatório enviado com sucesso.")
            return 0
        else:
            logger.error("❌ Falha ao enviar relatório via Telegram.")
            return 1

    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"Erro crítico inesperado:\n{error_detail}")
        send_error_alert(f"Erro crítico:\n{str(e)}\n\n{error_detail[:400]}")
        return 1

    finally:
        logger.info("Assistente de Inbox encerrado.")
        logger.info("═══════════════════════════════════════════\n")


if __name__ == "__main__":
    sys.exit(main())
