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

SYSTEM_PROMPT = """Você é um classificador inteligente de emails focado em extrema objetividade.
Sua tarefa é analisar o email e retornar EXCLUSIVAMENTE um JSON válido.

Categorias obrigatórias:
1. "Acao_Necessaria": Emails que exigem atitude imediata (aprovações em processos seletivos, entrevistas, envio de documentos, demandas urgentes).
2. "Pessoal": Mensagens diretas de seres humanos conhecidos.
3. "Oportunidade": Vagas EXCLUSIVAMENTE para posições de Estágio (Estágio, Estagiário, Intern). Se for nível Junior, Pleno, Sênior, ou não especificar, classifique imediatamente como "Spam".
4. "Outros": Notificações de sistemas (GitHub, Vercel, Google), alertas de segurança, recibos, comunicações rotineiras que não exigem ação.
5. "Spam": Marketing, promoções, newsletters genéricas, vagas fora do perfil.

Formato de resposta JSON:
{
  "categoria": "<uma das 5 categorias acima>",
  "subtag": "<Uma palavra curta que defina o assunto. Ex: Entrevista, Documento, Segurança, GitHub, Lancer>",
  "remetente_identificado": "<Nome curto da empresa ou pessoa. Ex: Pitang, Google, Leonard>",
  "resumo": "<Para Acao_Necessaria, Pessoal e Outros: O que aconteceu e o que deve ser feito. Máximo 2 linhas.>",
  "foco": "<APENAS PARA Oportunidade: Qual a área técnica? Ex: Segurança da Informação, Embarcados, Web>",
  "analise": "<APENAS PARA Oportunidade: Vale a pena? Exige o quê? Máximo 2 linhas.>"
}
"""

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
        "max_tokens": 800,
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
                    
                    # Limpeza do markdown para o Python não quebrar
                    content = content.replace("```json", "").replace("```", "").strip()
                    
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
            "maxOutputTokens": 800,
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
    Classifica um email. Possui um pré-filtro para evitar gastos com LLM
    em emails óbvios de plataformas de vagas que não são estágio.
    """
    assunto_lower = email_data.get('subject', '').lower()
    remetente_lower = email_data.get('sender', '').lower()
    
    # 1. PRÉ-FILTRO DE VAGAS: Verifica se é plataforma e se tem palavras-chave
    plataformas = ["glassdoor", "linkedin", "gupy", "vagas.com", "infojobs"]
    palavras_estagio = ["estágio", "estagio", "estagiário", "estagiario", "intern", "internship"]
    
    veio_de_plataforma = any(plat in remetente_lower for plat in plataformas)
    tem_estagio_no_assunto = any(palavra in assunto_lower for palavra in palavras_estagio)

    if veio_de_plataforma and not tem_estagio_no_assunto:
        logger.info("Bloqueado no pré-filtro: Vaga genérica (não é estágio).")
        return {
            "categoria": "Spam",
            "destaque": False,
            "remetente_identificado": email_data.get("sender", "Plataforma de Vagas"),
            "resumo": "Vaga irrelevante descartada automaticamente (não contém termos de estágio)."
        }

    # 2. CONTINUA PARA A IA SE PASSAR NO FILTRO
    groq_key = os.getenv("GROQ_API_KEY", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")

    email_content = f"Assunto: {email_data.get('subject', '')}\nRemetente: {email_data.get('sender', '')}\n\nCorpo:\n{email_data.get('body', '')}"
    result = None

    if groq_key:
        result = _call_groq(groq_key, email_content)
    
    if not result and gemini_key:
        result = _call_gemini(gemini_key, email_content)

    if not result:
        result = {
            "categoria": "Indefinido",
            "subtag": "Erro",
            "remetente_identificado": email_data.get("sender", "Desconhecido"),
            "resumo": "Erro na API da IA ao ler email muito longo.",
            "foco": "",
            "analise": ""
        }

    result.setdefault("categoria", "Indefinido")
    result.setdefault("subtag", "Aviso")
    result.setdefault("remetente_identificado", email_data.get("sender", "Desconhecido")[:15])
    result.setdefault("resumo", "(sem resumo)")
    result.setdefault("foco", "")
    result.setdefault("analise", "")

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
