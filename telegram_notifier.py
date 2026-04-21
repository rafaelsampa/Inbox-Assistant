"""
telegram_notifier.py
--------------------
Módulo responsável por formatar e enviar o relatório de emails via Telegram.
Usa requisições HTTP diretas (urllib), sem dependências externas.
"""

import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ─── Emojis e mapeamento de categorias ──────────────────────────────────────

CATEGORIA_CONFIG = {
    "Pessoal":                  {"emoji": "[Pess]", "ordem": 2},
    "Profissional_Positivo":    {"emoji": "[Aprovado]", "ordem": 0},
    "Profissional_Negativo":    {"emoji": "[Recusa]", "ordem": 3},
    "Profissional_Oportunidade":{"emoji": "[Vaga]", "ordem": 1},
    "Spam":                     {"emoji": "[Spam]", "ordem": 5},
    "Indefinido":               {"emoji": "[?]", "ordem": 4},
}


def _send_message(bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """
    Envia uma mensagem via Bot API do Telegram.
    Retorna True se enviado com sucesso, False caso contrário.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("ok"):
                return True
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return False
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error(f"Telegram HTTP {e.code}: {body[:300]}")
    except urllib.error.URLError as e:
        logger.error(f"Telegram URLError: {e.reason}")
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar Telegram: {e}")

    return False


def _split_message(text: str, max_length: int = 4096) -> list[str]:
    """
    Divide uma mensagem longa em partes menores respeitando o limite do Telegram (4096 chars).
    Tenta quebrar em linhas para não cortar no meio de uma palavra.
    """
    if len(text) <= max_length:
        return [text]

    parts = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_length:
            parts.append(current)
            current = line + "\n"
        else:
            current += line + "\n"
    if current:
        parts.append(current)

    return parts


def _format_email_block(email_data: dict, index: int) -> str:
    """
    Formata um único email como bloco HTML para o Telegram.
    """
    clf = email_data.get("classificacao", {})
    categoria = clf.get("categoria", "Indefinido")
    config = CATEGORIA_CONFIG.get(categoria, {"emoji": "❓"})
    emoji = config["emoji"]
    destaque = clf.get("destaque", False)
    remetente = clf.get("remetente_identificado") or email_data.get("sender", "Desconhecido")
    resumo = clf.get("resumo", "(sem resumo)")
    subject = email_data.get("subject", "(sem assunto)")

    # Sanitiza para HTML do Telegram
    def esc(s: str) -> str:
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    destaque_str = " ⭐ DESTAQUE" if destaque else ""
    linha = (
        f"{emoji} <b>{esc(subject)}</b>{destaque_str}\n"
        f"👤 {esc(remetente)}\n"
        f"💬 {esc(resumo)}"
    )
    return linha


def format_report(emails: list[dict]) -> list[str]:
    """
    Formata o relatório completo com todos os emails classificados.
    Retorna lista de strings (partes) para envio no Telegram.

    Agrupa por categoria e ordena por prioridade.
    """
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%Mh UTC")
    total = len(emails)

    if total == 0:
        msg = (
            f"📬 <b>Relatório de Inbox</b> — {now}\n\n"
            f"✨ Nenhum email novo nos últimos 4 horas."
        )
        return [msg]

    # Contagem por categoria
    counts: dict[str, int] = {}
    for e in emails:
        cat = e.get("classificacao", {}).get("categoria", "Indefinido")
        counts[cat] = counts.get(cat, 0) + 1

    # Cabeçalho
    header = f"📬 <b>Relatório de Inbox</b> — {now}\n"
    header += f"📊 <b>{total} email(s) novo(s):</b>"
    for cat, n in sorted(counts.items(), key=lambda x: CATEGORIA_CONFIG.get(x[0], {}).get("ordem", 99)):
        cfg = CATEGORIA_CONFIG.get(cat, {"emoji": "❓"})
        header += f"\n  {cfg['emoji']} {cat}: {n}"
    header += "\n" + "─" * 18

    # Ordena emails por prioridade de categoria e destaque
    def sort_key(e):
        clf = e.get("classificacao", {})
        cat = clf.get("categoria", "Indefinido")
        ordem = CATEGORIA_CONFIG.get(cat, {}).get("ordem", 99)
        destaque = 0 if clf.get("destaque") else 1
        return (destaque, ordem)

    sorted_emails = sorted(emails, key=sort_key)

    # Bloco de cada email (pula spam por padrão, apenas conta)
    blocks = [header]
    spam_count = 0

    for i, email_data in enumerate(sorted_emails, 1):
        clf = email_data.get("classificacao", {})
        if clf.get("categoria") == "Spam":
            spam_count += 1
            continue
        blocks.append(_format_email_block(email_data, i))

    if spam_count > 0:
        blocks.append(f"🗑️ <i>{spam_count} email(s) de spam ignorados.</i>")

    # Junta em uma mensagem e divide se necessário
    full_message = "\n\n".join(blocks)
    return _split_message(full_message)


def send_report(emails: list[dict]) -> bool:
    """
    Ponto de entrada principal: formata e envia o relatório via Telegram.
    Lê BOT_TOKEN e CHAT_ID das variáveis de ambiente.

    Retorna True se enviado com sucesso.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados.")
        return False

    parts = format_report(emails)
    all_ok = True

    for i, part in enumerate(parts, 1):
        logger.info(f"Enviando parte {i}/{len(parts)} do relatório ({len(part)} chars)...")
        ok = _send_message(bot_token, chat_id, part)
        if not ok:
            logger.error(f"Falha ao enviar parte {i} do relatório.")
            all_ok = False

    return all_ok


def send_error_alert(error_message: str) -> None:
    """
    Envia um alerta de erro crítico via Telegram.
    Usado para notificar falhas no pipeline principal.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        logger.warning("Não foi possível enviar alerta de erro: credenciais Telegram ausentes.")
        return

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%Mh UTC")
    msg = (
        f"⚠️ <b>ERRO no Assistente de Inbox</b> — {now}\n\n"
        f"<code>{error_message[:500]}</code>"
    )
    _send_message(bot_token, chat_id, msg)
