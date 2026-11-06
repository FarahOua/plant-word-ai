"""Page « Évaluation du workflow » : lance les questions de test et recueille les avis."""

import streamlit as st

from services.api_client import ApiError, get_evaluation_cases, run_evaluation_case, send_evaluation_feedback

JUDGE_BADGES = {
    "correct": "✅ correcte",
    "incorrect": "❌ incorrecte",
    "non configuré": "⚪ juge non configuré",
    "erreur": "⚠️ erreur du juge",
}


def _init_state() -> bool:
    """Charge les questions une seule fois. Renvoie False si le backend est injoignable."""
    if "eval_suite" not in st.session_state:
        try:
            suite = get_evaluation_cases()
        except ApiError as error:
            st.error(str(error))
            return False
        st.session_state.eval_suite = suite
        st.session_state.eval_cases = list(suite["cases"])
        st.session_state.eval_results = {}  # case_id -> résultat du backend
        st.session_state.eval_human = {}    # case_id -> "correct" / "incorrect"
    return True


def _run(case: dict) -> None:
    try:
        st.session_state.eval_results[case["id"]] = run_evaluation_case(case)
    except ApiError as error:
        st.session_state.eval_results[case["id"]] = {
            "answer": None, "error": str(error), "seconds": 0,
            "rules": {"passed": False, "failures": [str(error)]},
            "judge": {"verdict": "erreur", "reason": str(error)},
        }
    st.session_state.eval_human.pop(case["id"], None)  # nouvelle réponse = nouvel avis


def _give_feedback(case: dict, verdict: str) -> None:
    result = st.session_state.eval_results[case["id"]]
    try:
        send_evaluation_feedback({
            "case_id": case["id"],
            "message": case["message"],
            "label": case["label"],
            "answer": result["answer"],
            "verdict": verdict,
            "judge_verdict": result["judge"]["verdict"],
        })
    except ApiError as error:
        st.toast(f"Avis non enregistré : {error}", icon="⚠️")
        return
    st.session_state.eval_human[case["id"]] = verdict


def _summary(cases: list[dict]) -> None:
    results = st.session_state.eval_results
    human = st.session_state.eval_human
    done = [c["id"] for c in cases if c["id"] in results]
    if not done:
        return

    rules_ok = sum(results[i]["rules"]["passed"] for i in done)
    judge_ok = sum(results[i]["judge"]["verdict"] == "correct" for i in done)
    human_ok = sum(v == "correct" for v in human.values())
    compared = [i for i in human if results.get(i, {}).get("judge", {}).get("verdict") in ("correct", "incorrect")]
    agree = sum(human[i] == results[i]["judge"]["verdict"] for i in compared)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Règles", f"{rules_ok}/{len(done)}")
    col2.metric("Juge LLM", f"{judge_ok}/{len(done)}")
    col3.metric("Avis humain", f"{human_ok}/{len(human)}" if human else "–")
    col4.metric("Accord juge / humain", f"{agree}/{len(compared)}" if compared else "–")


def _add_case_form(labels: dict) -> None:
    with st.expander("➕ Ajouter une question"):
        with st.form("add_case", clear_on_submit=True):
            message = st.text_input("Question")
            label = st.selectbox(
                "Photo importée (classe PlantVillage)",
                list(labels),
                format_func=lambda key: f"{labels[key]['plant']} – {labels[key]['disease'] or 'saine'}  ({key})",
            )
            expected = st.text_area(
                "Réponse attendue (pour le juge LLM, facultatif)",
                placeholder="Ex. : il doit donner uniquement les traitements chimiques de la tavelure.",
            )
            if st.form_submit_button("Ajouter") and message.strip():
                st.session_state.eval_cases.append({
                    "id": f"perso_{len(st.session_state.eval_cases) + 1}",
                    "category": "personnalisée",
                    "label": label,
                    "message": message.strip(),
                    "expected": expected.strip(),
                })
                st.rerun()


def _case_card(case: dict, labels: dict) -> None:
    diagnosis = labels[case["label"]]
    result = st.session_state.eval_results.get(case["id"])

    with st.container(border=True):
        head, button = st.columns([5, 1])
        head.markdown(f"**{case['message']}**")
        head.caption(
            f"{case['category']} · photo : {diagnosis['plant']} – {diagnosis['disease'] or 'saine'} ({case['label']})"
        )
        if button.button("▶️ Lancer", key=f"run_{case['id']}", width="stretch"):
            with st.spinner("Appel du workflow et du juge…"):
                _run(case)
            st.rerun()

        if case.get("expected"):
            st.caption(f"Attendu : {case['expected']}")

        if result is None:
            return

        with st.expander("Body envoyé au workflow"):
            st.json(result.get("body") or {})

        if result["error"]:
            st.error(result["error"])
            return

        st.markdown(result["answer"])

        rules, judge = result["rules"], result["judge"]
        rules_text = "✅ règles respectées" if rules["passed"] else "❌ " + " ; ".join(rules["failures"])
        st.caption(f"⏱ {result['seconds']} s · Règles : {rules_text}")
        st.caption(f"Juge LLM : {JUDGE_BADGES.get(judge['verdict'], judge['verdict'])} — {judge['reason']}")

        human = st.session_state.eval_human.get(case["id"])
        label, ok_col, ko_col = st.columns([3, 1, 1])
        label.markdown(
            "Votre avis : " + {"correct": "✅ **correcte**", "incorrect": "❌ **incorrecte**"}.get(human, "_à donner_")
        )
        if ok_col.button("✅ Correcte", key=f"ok_{case['id']}", width="stretch",
                         type="primary" if human == "correct" else "secondary"):
            _give_feedback(case, "correct")
            st.rerun()
        if ko_col.button("❌ Incorrecte", key=f"ko_{case['id']}", width="stretch",
                         type="primary" if human == "incorrect" else "secondary"):
            _give_feedback(case, "incorrect")
            st.rerun()


def render() -> None:
    """Affiche la page d'évaluation."""
    if st.button("← Retour à l'analyse"):
        st.session_state.page = "analyse"
        st.rerun()

    st.title("🧪 Évaluation du workflow")
    st.caption(
        "Chaque question est envoyée au workflow n8n avec un nouveau sessionId. "
        "La réponse est vérifiée par des règles simples et par un LLM juge, puis vous donnez votre avis."
    )

    if not _init_state():
        return

    labels = st.session_state.eval_suite["labels"]
    cases = st.session_state.eval_cases

    run_all, reset = st.columns([3, 1])
    if run_all.button(f"▶️ Lancer tout ({len(cases)} questions)", type="primary", width="stretch"):
        progress = st.progress(0.0, text="Démarrage…")
        for index, case in enumerate(cases, 1):
            progress.progress((index - 1) / len(cases), text=f"{index}/{len(cases)} : {case['message']}")
            _run(case)
        progress.progress(1.0, text="Terminé")
        st.rerun()
    if reset.button("Effacer", width="stretch"):
        st.session_state.eval_results = {}
        st.session_state.eval_human = {}
        st.rerun()

    _summary(cases)
    _add_case_form(labels)

    for case in cases:
        _case_card(case, labels)
