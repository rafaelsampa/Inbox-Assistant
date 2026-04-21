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

def _send_message(bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Envia uma mensagem via Bot API do Telegram."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8")).get("ok", False)
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram: {e}")
        return False

def _split_message(text: str, max_length: int = 4096) -> list[str]:
    """Divide a mensagem para não estourar o limite do Telegram."""
    if len(text) <= max_length: return [text]
    parts, current = [], ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_length:
            parts.append(current)
            current = line + "\n"
        else:
            current += line + "\n"
    if current: parts.append(current)
    return parts

def format_report(emails: list[dict]) -> list[str]:
    """Constrói o Boletim de Inbox no formato Ação e Contexto."""
    now_str = datetime.now(timezone.utc).strftime("%H:%Mh UTC")
    
    if not emails:
        return [f"📬 <b>Boletim de Inbox ({now_str})</b>\n\n✨ Nenhum email novo."]

    # Separação de lixo eletrônico
    relevantes = [e for e in emails if e.get("classificacao", {}).get("categoria") != "Spam"]
    spam_count = len(emails) - len(relevantes)

    # Cabeçalho limpo
    header = f"📬 <b>Boletim de Inbox ({now_str})</b>\n"
    header += f"{len(relevantes)} emails relevantes | {spam_count} spams filtrados\n"

    grupos = {"Acao_Necessaria": [], "Pessoal": [], "Oportunidade": [], "Outros": [], "Indefinido": []}
    for e in relevantes:
        cat = e.get("classificacao", {}).get("categoria", "Indefinido")
        if cat not in grupos: cat = "Indefinido"
        grupos[cat].append(e)

    blocks = [header.strip()]
    def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    if grupos["Acao_Necessaria"]:
        sec = "🚨 <b>Ação Necessária</b>\n"
        for e in grupos["Acao_Necessaria"]:
            clf = e.get("classificacao", {})
            sec += f"• <b>[{esc(clf.get('subtag', 'Aviso'))}] {esc(clf.get('remetente_identificado', 'Desconhecido'))}:</b> {esc(clf.get('resumo', ''))}\n"
        blocks.append(sec.strip())

    if grupos["Pessoal"]:
        sec = "👤 <b>Pessoal</b>\n"
        for e in grupos["Pessoal"]:
            clf = e.get("classificacao", {})
            sec += f"• <b>[{esc(clf.get('subtag', 'Mensagem'))}] {esc(clf.get('remetente_identificado', 'Desconhecido'))}:</b> {esc(clf.get('resumo', ''))}\n"
        blocks.append(sec.strip())

    if grupos["Oportunidade"]:
        sec = "🚀 <b>Oportunidades (Estágio)</b>\n"
        for e in grupos["Oportunidade"]:
            clf = e.get("classificacao", {})
            sec += f"• <b>{esc(clf.get('remetente_identificado', 'Empresa'))} : {esc(clf.get('subtag', 'Estágio'))}</b>\n"
            sec += f"  <b>Foco:</b> {esc(clf.get('foco', 'N/A'))}\n"
            sec += f"  <b>Análise:</b> {esc(clf.get('analise', 'N/A'))}\n"
        blocks.append(sec.strip())

    if grupos["Outros"] or grupos["Indefinido"]:
        sec = "📌 <b>Outros</b>\n"
        for cat in ["Outros", "Indefinido"]:
            for e in grupos[cat]:
                clf = e.get("classificacao", {})
                sec += f"• <b>[{esc(clf.get('subtag', 'Sistema'))}] {esc(clf.get('remetente_identificado', 'Serviço'))}:</b> {esc(clf.get('resumo', ''))}\n"
        blocks.append(sec.strip())

    return _split_message("\n\n".join(blocks))

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
