"""Évaluation du workflow n8n PlantWorld AI.

Envoie chaque cas de test au webhook n8n (un nouveau sessionId par cas),
vérifie la réponse avec des règles simples et affiche un score.

Utilisation (depuis le dossier backend) :
    python evaluation/run_eval.py
    python evaluation/run_eval.py --only traitement_chimique cause_sans_plante
    python evaluation/run_eval.py --compare evaluation/results/20261105-153000.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

EVAL_DIR = Path(__file__).parent
load_dotenv(EVAL_DIR.parent / ".env")

# Mêmes règles que la page d'évaluation de l'interface
sys.path.insert(0, str(EVAL_DIR.parent))
from services.evaluation import build_case_body, check_rules as check  # noqa: E402


def call_workflow(url: str, api_key: str, timeout: int, body: dict) -> dict:
    """Envoie le body au webhook, exactement comme le backend."""
    headers = {"X-API-Key": api_key} if api_key else {}

    start = time.monotonic()
    try:
        response = requests.post(url, json=body, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        return {"answer": None, "error": str(error), "seconds": round(time.monotonic() - start, 1)}

    if isinstance(data, list) and data:
        data = data[0]
    answer = data.get("answer") or data.get("output") if isinstance(data, dict) else None
    return {"answer": answer, "error": None, "seconds": round(time.monotonic() - start, 1)}


def short(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def main() -> int:
    parser = argparse.ArgumentParser(description="Évalue le workflow n8n PlantWorld AI.")
    parser.add_argument("--cases", default=EVAL_DIR / "cases.json", type=Path, help="fichier des cas de test")
    parser.add_argument("--only", nargs="+", metavar="ID", help="ne lancer que ces cas")
    parser.add_argument("--compare", type=Path, metavar="RESULTATS.json", help="comparer avec un run précédent")
    parser.add_argument("--url", default=os.getenv("N8N_WEBHOOK_URL"), help="URL du webhook (défaut : .env)")
    args = parser.parse_args()

    if not args.url:
        print("N8N_WEBHOOK_URL manquant (backend/.env ou --url).")
        return 2

    api_key = os.getenv("N8N_API_KEY", "")
    timeout = int(os.getenv("N8N_TIMEOUT") or 60)

    suite = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = suite["cases"]
    if args.only:
        cases = [c for c in cases if c["id"] in args.only]
        if not cases:
            print(f"Aucun cas trouvé pour {args.only}.")
            return 2

    previous = {}
    if args.compare:
        previous = {r["id"]: r for r in json.loads(args.compare.read_text(encoding="utf-8"))["results"]}

    print(f"Webhook : {args.url}")
    print(f"{len(cases)} cas à évaluer\n")

    results = []
    for index, case in enumerate(cases, 1):
        body = build_case_body(case)
        print(f"[{index}/{len(cases)}] {case['id']} … ", end="", flush=True)

        call = call_workflow(args.url, api_key, timeout, body)
        failures = [f"erreur : {call['error']}"] if call["error"] else check(case, call["answer"])
        passed = not failures

        change = ""
        if case["id"] in previous:
            was = previous[case["id"]]["passed"]
            if was and not passed:
                change = "  ↓ RÉGRESSION"
            elif not was and passed:
                change = "  ↑ corrigé"

        print(f"{'OK ' if passed else 'ÉCHEC'} ({call['seconds']} s){change}")
        if not passed:
            print(f"      → {'; '.join(failures)}")
            print(f"      réponse : {short((call['answer'] or '').replace(chr(10), ' '), 160)}")

        results.append({
            "id": case["id"],
            "category": case["category"],
            "message": case["message"],
            "label": case["label"],
            "body": body,
            "passed": passed,
            "failures": failures,
            "seconds": call["seconds"],
            "answer": call["answer"],
            "previous_answer": previous.get(case["id"], {}).get("answer"),
        })

    # Résumé par catégorie
    print("\nRésumé par catégorie")
    categories = {}
    for r in results:
        ok, total = categories.get(r["category"], (0, 0))
        categories[r["category"]] = (ok + r["passed"], total + 1)
    for name, (ok, total) in categories.items():
        print(f"  {name:<15} {ok}/{total}")

    score = sum(r["passed"] for r in results)
    print(f"\nScore : {score}/{len(results)} ({round(100 * score / len(results))} %)")
    if previous:
        old_score = sum(r["passed"] for r in previous.values() if r["id"] in {c["id"] for c in cases})
        print(f"Run précédent : {old_score}/{len(results)}")

    out_dir = EVAL_DIR / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out_file.write_text(
        json.dumps(
            {"date": datetime.now().isoformat(timespec="seconds"), "webhook": args.url,
             "score": score, "total": len(results), "results": results},
            ensure_ascii=False, indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Détail des réponses : {out_file.relative_to(EVAL_DIR.parent)}")

    return 0 if score == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
