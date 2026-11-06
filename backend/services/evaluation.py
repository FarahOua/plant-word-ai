"""Évaluation du workflow n8n : cas de test, contrôles par règles, juge LLM et avis humains."""

import json
import re
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

import requests
from flask import current_app

from services.chatbot import ChatbotUnavailableError, build_payload, send_to_n8n
from services.labels import PLANTVILLAGE_LABELS, describe_label

EVAL_DIR = Path(__file__).parent.parent / "evaluation"
CASES_FILE = EVAL_DIR / "cases.json"
FEEDBACK_FILE = EVAL_DIR / "feedback.jsonl"

SOURCE_PATTERN = re.compile(r"https?://\S+")


class EvaluationError(ValueError):
    """Requête d'évaluation invalide."""


# --- Cas de test -----------------------------------------------------------

def load_suite() -> dict:
    """Renvoie les questions de cases.json et les classes PlantVillage disponibles."""
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]
    labels = {label: {"plant": plant, "disease": disease} for label, (plant, disease) in PLANTVILLAGE_LABELS.items()}
    return {"cases": cases, "labels": labels}


def build_analysis(label: str) -> dict:
    """Résultat d'analyse simulé, comme si l'utilisateur avait importé une photo de cette classe."""
    plant, disease = describe_label(label)
    return {
        "recognized": True,
        "label": label,
        "plant": plant,
        "disease": disease,
        "is_healthy": disease is None,
        "confidence": 1,
    }


def build_case_body(case: dict) -> dict:
    """Body envoyé au webhook n8n pour un cas : même format que l'application."""
    return build_payload(f"eval-{uuid.uuid4()}", case["message"], build_analysis(case["label"]))


# --- Contrôles par règles ---------------------------------------------------

def normalize(text: str) -> str:
    """Minuscules, sans accents : « Tâches » et « taches » sont comparés pareil."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


# Mots très fréquents propres à chaque langue (sans les mots communs à plusieurs langues)
STOPWORDS = {
    "en": {"the", "is", "and", "of", "to", "it", "are", "by", "with", "your", "can", "this", "on", "not"},
    "fr": {"le", "les", "des", "est", "et", "du", "une", "sur", "avec", "vous", "pour", "dans", "ce", "pas", "je", "ne", "aux", "qu", "concernant"},
    "es": {"el", "los", "las", "es", "y", "del", "una", "con", "para", "por", "su", "sus", "hojas", "no"},
}


def detect_language(text: str) -> str | None:
    """Devine la langue (en / fr / es) d'après les mots courants. None si indécidable."""
    words = re.findall(r"[a-zà-ÿ]+", SOURCE_PATTERN.sub(" ", text.lower()))
    scores = {lang: sum(word in stop for word in words) for lang, stop in STOPWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def check_rules(case: dict, answer: str | None) -> list[str]:
    """Renvoie la liste des règles non respectées (vide = toutes respectées)."""
    if not answer or not answer.strip():
        return ["réponse vide"]

    text = normalize(answer)
    failures = []

    if any_of := case.get("must_contain_any"):
        if not any(normalize(word) in text for word in any_of):
            failures.append(f"aucun de {any_of}")

    for word in case.get("must_contain_all", []):
        if normalize(word) not in text:
            failures.append(f"manque « {word} »")

    for word in case.get("must_not_contain", []):
        if normalize(word) in text:
            failures.append(f"contient « {word} »")

    if pattern := case.get("must_match"):
        if not re.search(pattern, answer, re.IGNORECASE):
            failures.append(f"ne correspond pas à /{pattern}/")

    if pattern := case.get("must_not_match"):
        if match := re.search(pattern, answer, re.IGNORECASE):
            failures.append(f"contient « {match.group(0)} »")

    if expected_language := case.get("language"):
        detected = detect_language(answer)
        if detected != expected_language:
            failures.append(f"langue : {detected or '?'} au lieu de {expected_language}")

    has_source = bool(SOURCE_PATTERN.search(answer))
    if case.get("expect_source") is True and not has_source:
        failures.append("pas de source")
    if case.get("expect_source") is False and has_source:
        failures.append("source inattendue")

    if (max_length := case.get("max_length")) and len(answer) > max_length:
        failures.append(f"trop long ({len(answer)} > {max_length} car.)")

    return failures


# --- Juge LLM -----------------------------------------------------------------

JUDGE_PROMPT = """You evaluate a plant disease chatbot.

Photo diagnosis: {diagnosis}
User question: "{question}"
Expected answer: {expected}

Chatbot answer:
\"\"\"{answer}\"\"\"

Is the chatbot answer correct compared with the expected answer?
Judge the substance, not the wording: an explicit "yes" or a specific phrasing is never required, the key facts are enough.
But extra sections that were not asked (e.g. symptoms or control measures when only the cause was asked) still make the answer incorrect.
When the user asks to identify the problem ("what is it?", "what is <disease>?", "is it a virus?"), a list of symptoms is ALLOWED and is not an extra section (control measures are still not allowed).
The expected answer has priority over these rules: anything it describes as optional or allowed must never make the answer incorrect.
Be fair: a short sentence naming the disease or its pathogen, synonyms of scientific names, or extra detail on the requested topic are fine.
It is incorrect if it misses the expected content, answers in the wrong language, adds whole sections that were not asked, or invents facts.

Reply with a JSON object only:
{{"verdict": "correct" or "incorrect", "reason": "one short sentence in French"}}"""


def judge(case: dict, analysis: dict, answer: str) -> dict:
    """Demande à un LLM si la réponse est correcte. Renvoie {"verdict", "reason"}."""
    base_url = current_app.config["JUDGE_BASE_URL"]
    if not base_url:
        return {"verdict": "non configuré", "reason": "JUDGE_BASE_URL est vide dans backend/.env."}

    disease = analysis["disease"] or "healthy"
    prompt = JUDGE_PROMPT.format(
        diagnosis=f"{analysis['plant']} – {disease} ({analysis['label']})",
        question=case["message"],
        expected=case.get("expected") or "A correct, relevant answer to the question.",
        answer=answer,
    )
    api_key = current_app.config["JUDGE_API_KEY"]
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json={
                "model": current_app.config["JUDGE_MODEL"],
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            },
            headers=headers,
            timeout=current_app.config["N8N_TIMEOUT"],
        )
        response.raise_for_status()
        result = json.loads(response.json()["choices"][0]["message"]["content"])
    except (requests.RequestException, ValueError, KeyError, IndexError) as error:
        return {"verdict": "erreur", "reason": f"Juge indisponible : {error}"}

    verdict = str(result.get("verdict", "")).lower()
    return {
        "verdict": verdict if verdict in ("correct", "incorrect") else "erreur",
        "reason": str(result.get("reason", "")),
    }


# --- Exécution d'un cas ------------------------------------------------------------

def run_case(case: dict) -> dict:
    """Envoie la question au workflow n8n, puis applique les règles et le juge LLM."""
    if not isinstance(case, dict) or not str(case.get("message", "")).strip():
        raise EvaluationError("Le cas doit contenir une question ('message').")
    if case.get("label") not in PLANTVILLAGE_LABELS:
        raise EvaluationError(f"Label PlantVillage inconnu : {case.get('label')!r}.")

    # Nouveau sessionId à chaque cas : la mémoire n8n ne fausse pas le test
    body = build_case_body(case)

    start = datetime.now()
    try:
        answer, error = send_to_n8n(body), None
    except ChatbotUnavailableError as exc:
        answer, error = None, str(exc)
    seconds = round((datetime.now() - start).total_seconds(), 1)

    if error:
        return {"body": body, "answer": None, "error": error, "seconds": seconds,
                "rules": {"passed": False, "failures": [error]},
                "judge": {"verdict": "erreur", "reason": "Pas de réponse du workflow."}}

    failures = check_rules(case, answer)
    return {
        "body": body,
        "answer": answer,
        "error": None,
        "seconds": seconds,
        "rules": {"passed": not failures, "failures": failures},
        "judge": judge(case, body["analysis"], answer),
    }


# --- Avis humains ----------------------------------------------------------------

def save_feedback(data: dict) -> None:
    """Ajoute l'avis humain (correct / incorrect) dans evaluation/feedback.jsonl."""
    if not isinstance(data, dict) or data.get("verdict") not in ("correct", "incorrect"):
        raise EvaluationError("Le champ 'verdict' doit valoir 'correct' ou 'incorrect'.")

    entry = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "case_id": data.get("case_id"),
        "message": data.get("message"),
        "label": data.get("label"),
        "answer": data.get("answer"),
        "verdict": data["verdict"],
        "judge_verdict": data.get("judge_verdict"),
        "comment": data.get("comment") or None,
    }
    with FEEDBACK_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")
