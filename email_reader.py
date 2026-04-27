"""
email_reader.py
---------------
Módulo responsável por conectar ao servidor IMAP e buscar emails não lidos.
Usa apenas bibliotecas nativas do Python (imaplib, email).
"""

import imaplib
import email
import os
import logging
from email.header import decode_header
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def decode_mime_words(text: str) -> str:
    """Decodifica cabeçalhos MIME (ex: assunto e remetente com encoding)."""
    if not text:
        return ""
    decoded_parts = decode_header(text)
    result = []
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def extract_body(msg) -> str:
    """
    Extrai o corpo de texto do email.
    Prioriza text/plain; usa text/html como fallback (removendo tags).
    """
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            # Ignora anexos
            if "attachment" in disposition:
                continue

            if content_type == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                try:
                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                    break  # text/plain encontrado, para aqui
                except Exception as e:
                    logger.warning(f"Erro ao decodificar parte text/plain: {e}")

            elif content_type == "text/html" and not body:
                # Fallback HTML: remove tags básicas
                charset = part.get_content_charset() or "utf-8"
                try:
                    html = part.get_payload(decode=True).decode(charset, errors="replace")
                    import re
                    body = re.sub(r"<[^>]+>", " ", html)
                    body = re.sub(r"\s+", " ", body).strip()
                except Exception as e:
                    logger.warning(f"Erro ao decodificar parte text/html: {e}")
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            body = msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception as e:
            logger.warning(f"Erro ao decodificar corpo simples: {e}")

    return body.strip()


def fetch_unread_emails(
    imap_server: str,
    email_address: str,
    password: str,
    mailbox: str = "INBOX",
    hours_back: int = 4,
    max_emails: int = 50,
) -> list[dict]:
    """
    Conecta ao servidor IMAP e retorna uma lista de emails não lidos
    recebidos nas últimas `hours_back` horas.

    Retorna lista de dicts com keys:
        - uid, subject, sender, date, body
    """
    emails_data = []
    mail = None

    try:
        logger.info(f"Conectando ao IMAP: {imap_server}")
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        mail.select(mailbox)

        # Busca emails não lidos que AINDA NÃO tem a etiqueta da IA
        status, messages = mail.search(None, 'X-GM-RAW', 'is:unread -label:InboxAI-seen')
        if status != "OK":
            logger.error("Falha ao buscar emails UNSEEN.")
            return []

        uids = messages[0].split()
        logger.info(f"Emails não lidos encontrados: {len(uids)}")

        # Limite para evitar uso excessivo de API
        uids = uids[-max_emails:]

        # Threshold de tempo
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        for uid in uids:
            try:
                # O PEEK lê o conteúdo sem remover o status de "Não Lido"
                status, data = mail.fetch(uid, "(BODY.PEEK[])")
                if status != "OK":
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Data do email
                date_str = msg.get("Date", "")
                try:
                    from email.utils import parsedate_to_datetime
                    email_date = parsedate_to_datetime(date_str)
                    # Normaliza para UTC
                    if email_date.tzinfo is None:
                        email_date = email_date.replace(tzinfo=timezone.utc)
                    if email_date < cutoff:
                        continue  # Email fora da janela de tempo
                except Exception:
                    pass  # Se não conseguir parsear a data, inclui o email mesmo assim

                subject = decode_mime_words(msg.get("Subject", "(sem assunto)"))
                sender = decode_mime_words(msg.get("From", "(remetente desconhecido)"))
                body = extract_body(msg)

                # Limita o corpo a 3000 chars antes de enviar para a IA (economia de tokens)
                body_truncated = body[:3000] if body else "(corpo vazio)"

                emails_data.append({
                    "uid": uid.decode(),
                    "subject": subject,
                    "sender": sender,
                    "date": date_str,
                    "body": body_truncated,
                })

                # Applica o marcador do Gmail para auditoria
                try:
                    mail.store(uid, '+X-GM-LABELS', 'InboxAI-seen')
                    # Gmail re-adiciona \Seen ao manipular labels — remove explicitamente
                    mail.store(uid, '-FLAGS', '\\Seen')
                except Exception as e:
                    logger.warning(f"Erro ao adicionar tag ou restaurar status no email {uid}: {e}")

            except Exception as e:
                logger.warning(f"Erro ao processar email UID {uid}: {e}")
                continue

        logger.info(f"Emails dentro da janela de {hours_back}h: {len(emails_data)}")

    except imaplib.IMAP4.error as e:
        logger.error(f"Erro IMAP (autenticação ou conexão): {e}")
    except OSError as e:
        logger.error(f"Erro de rede ao conectar ao IMAP: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado no fetch de emails: {e}")
    finally:
        if mail:
            try:
                mail.logout()
            except Exception:
                pass

    return emails_data
