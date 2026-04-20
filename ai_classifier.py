"""
ai_classifier.py
----------------
Módulo de integração com LLMs para classificação e resumo de emails.
Suporta Groq (Llama 3) e Google Gemini, priorizando planos gratuitos.
Retorna JSON estruturado conforme as regras de negócio definidas no README.
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

# ─── Prompt do sistema ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é um classificador inteligente de emails. Sua tarefa é analisar o conteúdo
de um email e retornar EXCLUSIVAMENTE um JSON válido, sem qualquer texto adicional antes ou depois.

Categorias de classificação:
- "Pessoal": Mensagens de pessoas físicas conhecidas (familiares, amigos, colegas).
  Identifique quem é o remetente e qual a suposta relação.
- "Profissional_Positivo": Resposta POSITIVA de processo seletivo (aprovação, convite para entrevista).
- "Profissional_Negativo": Resposta NEGATIVA de processo seletivo (reprovação, agradecimento genérico).
- "Profissional_Oportunidade": Alerta de nova vaga de estágio em Ciência da Computação.
  Destaque especial se for nas áreas: Segurança da Informação, Criptografia, Infraestrutura de Software ou Sistemas Operacionais.
- "Spam": Lixo eletrônico, newsletters, promoções, notificações automáticas de sistemas.

Formato de resposta JSON obrigatório:
{
  "categoria": "<uma das categorias acima>",
  "destaque": <true se for Profissional_Positivo ou Oportunidade em área técnica prioritária, false caso contrário>,
  "remetente_identificado": "<quem é o remetente, ex: 'Recrutadora da Empresa X', 'Colega de faculdade João'> ou null",
  "resumo": "<resumo direto do conteúdo do email, máximo 100 palavras, em português, linguagem objetiva>"
}

IMPORTANTE: Retorne APENAS o JSON. Sem markdown, sem explicações, sem blocos de código."""


def _call_groq(api_key: str, email_content: str, model: str = "llama3-8b-8192") -> dict | None:
    """
    Chama a API da Groq Cloud.
    Documentação: https://console.groq.com/docs/openai
    Groq é compatível com o formato OpenAI.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": email_content},
        ],
        "temperature": 0.1,
        "max_tokens": 400,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()
            return json.loads(content)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error(f"Groq HTTP {e.code}: {body[:300]}")
    except urllib.error.URLError as e:
        logger.error(f"Groq URLError (timeout ou rede): {e.reason}")
    except json.JSONDecodeError as e:
        logger.error(f"Groq retornou JSON inválido: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado Groq: {e}")

    return None


def _call_gemini(api_key: str, email_content: str, model: str = "gemini-1.5-flash") -> dict | None:
    """
    Chama a API do Google Gemini (plano gratuito).
    Documentação: https://ai.google.dev/api/rest
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT + "\n\n---\n\n" + email_content}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 400,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Remove possíveis markdown fences
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error(f"Gemini HTTP {e.code}: {body[:300]}")
    except urllib.error.URLError as e:
        logger.error(f"Gemini URLError (timeout ou rede): {e.reason}")
    except json.JSONDecodeError as e:
        logger.error(f"Gemini retornou JSON inválido: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado Gemini: {e}")

    return None


def classify_email(email_data: dict) -> dict:
    """
    Classifica um email usando a LLM configurada.
    Tenta Groq primeiro; se falhar, tenta Gemini; se ambos falharem,
    retorna classificação padrão 'Indefinido'.

    Parâmetros:
        email_data: dict com keys subject, sender, body

    Retorna:
        dict com keys: categoria, destaque, remetente_identificado, resumo
    """
    groq_key = os.getenv("GROQ_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    # Monta o conteúdo que será enviado para a LLM
    email_content = f"""Assunto: {email_data.get('subject', '')}
Remetente: {email_data.get('sender', '')}
Data: {email_data.get('date', '')}

Corpo do email:
{email_data.get('body', '')}"""

    result = None

    # Tenta Groq
    if groq_key:
        logger.info("Tentando classificar via Groq...")
        result = _call_groq(groq_key, email_content)
        if result:
            logger.info(f"Groq classificou como: {result.get('categoria')}")

    # Fallback Gemini
    if not result and gemini_key:
        logger.info("Groq falhou ou não configurado. Tentando Gemini...")
        result = _call_gemini(gemini_key, email_content)
        if result:
            logger.info(f"Gemini classificou como: {result.get('categoria')}")

    # Fallback padrão se ambos falharem
    if not result:
        logger.warning("Ambas as APIs falharam. Usando classificação padrão.")
        result = {
            "categoria": "Indefinido",
            "destaque": False,
            "remetente_identificado": email_data.get("sender", "Desconhecido"),
            "resumo": f"Assunto: {email_data.get('subject', '(sem assunto)')} — Não foi possível classificar este email automaticamente.",
        }

    # Garante que todas as keys existam no resultado
    result.setdefault("categoria", "Indefinido")
    result.setdefault("destaque", False)
    result.setdefault("remetente_identificado", None)
    result.setdefault("resumo", "(sem resumo)")

    return result


def classify_emails_batch(
    emails: list[dict], delay_between_calls: float = 1.0
) -> list[dict]:
    """
    Classifica uma lista de emails, adicionando os resultados da IA
    a cada email. Respeita um delay entre chamadas para evitar rate limits.

    Retorna lista de emails enriquecidos com key 'classificacao'.
    """
    enriched = []
    total = len(emails)

    for i, email_data in enumerate(emails, 1):
        logger.info(f"Classificando email {i}/{total}: {email_data.get('subject', '')[:50]}")
        classification = classify_email(email_data)
        enriched.append({**email_data, "classificacao": classification})

        if i < total:
            time.sleep(delay_between_calls)

    return enriched
