"""
ai_classifier.py
----------------
Integração exclusiva com Google Gemini para classificação de emails.
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um classificador inteligente de emails focado em extrema objetividade.
Sua tarefa é analisar o email e retornar EXCLUSIVAMENTE um JSON válido.

Categorias obrigatórias:
1. "Acao_Necessaria": Emails que exigem atitude imediata (aprovações, entrevistas, documentos).
2. "Pessoal": Mensagens diretas de seres humanos conhecidos.
3. "Oportunidade": Vagas EXCLUSIVAMENTE para posições de Estágio (Estágio, Estagiário, Intern). Se for nível Junior, Pleno, Sênior, classifique como "Spam".
4. "Outros": Notificações de sistemas, alertas, recibos, comunicações sem ação.
5. "Spam": Marketing, promoções, newsletters, vagas fora do perfil.

Formato de resposta JSON:
{
  "categoria": "<uma das 5 categorias acima>",
  "subtag": "<Uma palavra curta que defina o assunto. Ex: Entrevista, Segurança, GitHub>",
  "remetente_identificado": "<Nome curto da empresa ou pessoa>",
  "resumo": "<O que aconteceu e o que deve ser feito. Máximo 2 linhas.>",
  "foco": "<APENAS PARA Oportunidade: Qual a área técnica?>",
  "analise": "<APENAS PARA Oportunidade: Vale a pena? Exige o quê?>"
}
"""
def _call_gemini(api_key: str, email_content: str) -> dict | None:
    # gemini-2.0-flash é o modelo Flash atual e gratuito (substitui o 1.5-flash)
    model = "gemini-2.0-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    payload = {
        "contents": [{"parts": [{"text": SYSTEM_PROMPT + "\n\n---\n\n" + email_content}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 800,
            # Força saída JSON — elimina o problema de markdown fences no retorno
            "responseMimeType": "application/json",
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            # responseMimeType já previne fences, mas o .replace é defesa extra
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
    except urllib.error.HTTPError as e:
        logger.error(f"Gemini HTTP {e.code}: {e.read().decode('utf-8')[:300]}")
    except Exception as e:
        logger.error(f"Erro Gemini: {e}")

    return None



def classify_email(email_data: dict) -> dict:
    assunto_lower = email_data.get('subject', '').lower()
    remetente_lower = email_data.get('sender', '').lower()
    
    # Adicionado Jooble e Indeed no pre-filtro
    plataformas = ["glassdoor", "linkedin", "gupy", "vagas.com", "infojobs", "jooble", "indeed"]
    palavras_estagio = ["estágio", "estagio", "estagiário", "estagiario", "intern", "internship"]
    
    veio_de_plataforma = any(plat in remetente_lower for plat in plataformas)
    tem_estagio = any(palavra in assunto_lower for palavra in palavras_estagio)

    if veio_de_plataforma and not tem_estagio:
        return {
            "categoria": "Spam", "subtag": "Filtro",
            "remetente_identificado": "Plataforma de Vagas",
            "resumo": "Vaga irrelevante descartada automaticamente.",
            "foco": "", "analise": ""
        }

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    email_content = f"Assunto: {email_data.get('subject', '')}\nDe: {email_data.get('sender', '')}\n\nCorpo:\n{email_data.get('body', '')}"
    
    result = _call_gemini(gemini_key, email_content) if gemini_key else None

    if not result:
        result = {
            "categoria": "Indefinido", "subtag": "Erro API",
            "remetente_identificado": email_data.get("sender", "Desconhecido")[:15],
            "resumo": "Falha na comunicação com a API do Google Gemini.",
            "foco": "", "analise": ""
        }

    result.setdefault("categoria", "Indefinido")
    result.setdefault("subtag", "Aviso")
    result.setdefault("remetente_identificado", "Desconhecido")
    result.setdefault("resumo", "(sem resumo)")
    result.setdefault("foco", "")
    result.setdefault("analise", "")

    return result

def classify_emails_batch(emails: list[dict], delay_between_calls: float = 1.0) -> list[dict]:
    enriched = []
    for i, email_data in enumerate(emails, 1):
        logger.info(f"Classificando {i}/{len(emails)}: {email_data.get('subject', '')[:40]}")
        enriched.append({**email_data, "classificacao": classify_email(email_data)})
        if i < len(emails):
            time.sleep(delay_between_calls)
    return enriched