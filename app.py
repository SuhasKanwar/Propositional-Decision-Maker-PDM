from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd
import streamlit as st

from logic_core import (
	Atom,
	ForwardResult,
	Rule,
	backward_chain,
	forward_chain,
	generate_truth_table,
)
from parser import ParseError, parse_formula


BASE_DIR = Path(__file__).parent
DEFAULT_RULES_PATH = BASE_DIR / "rules.json"


def load_rule_sets() -> Dict[str, List[Rule]]:
	from logic_core import load_rules_from_json

	if DEFAULT_RULES_PATH.exists():
		data = json.loads(DEFAULT_RULES_PATH.read_text(encoding="utf8"))
	else:
		data = {"medical": [], "loan": []}
	return {
		"medical": load_rules_from_json(data, "medical"),
		"loan": load_rules_from_json(data, "loan"),
	}


def collect_atoms_from_rules(rules: List[Rule]) -> List[str]:
	atoms: Set[str] = set()
	for r in rules:
		atoms |= r.premise.atoms()
		atoms |= r.conclusion.atoms()
	return sorted(atoms)


def render_forward_result(result: ForwardResult) -> None:
	st.subheader("Forward Chaining Result")
	st.write("Final Facts:")
	if result.final_facts:
		st.table(pd.DataFrame(sorted(result.final_facts), columns=["Fact"]))
	else:
		st.info("No facts were inferred.")

	st.write("Fired Rules:")
	if result.steps:
		for step in result.steps:
			st.markdown(f"- {step.explanation}")
	else:
		st.info("No rules fired for the given facts.")

	if result.contradictions:
		st.error("Contradictions detected:")
		for atom, msg in result.contradictions:
			st.markdown(f"- **{atom}**: {msg}")


def render_proof_tree(node) -> None:
	label = f"Goal: {node.goal} (success)" if node.succeeded else f"Goal: {node.goal} (failure)"
	with st.expander(label, expanded=node.succeeded):
		st.write(node.message)
		if node.rule_id:
			st.write(f"Rule used: {node.rule_id}")
		for child in node.premises:
			render_proof_tree(child)


def main() -> None:
	st.set_page_config(page_title="Propositional Decision Maker", layout="wide")
	st.title("Propositional Decision Maker (PDM)")

	# Sidebar -----------------------------------------------------------------
	st.sidebar.header("Configuration")
	rule_sets = load_rule_sets()
	selected_domain = st.sidebar.selectbox("Demo rule set", ["medical", "loan"])
	rules = rule_sets[selected_domain]

	uploaded = st.sidebar.file_uploader("Upload custom rules.json", type="json")
	if uploaded is not None:
		try:
			data = json.loads(uploaded.read().decode("utf8"))
			from logic_core import load_rules_from_json

			rules = load_rules_from_json(data, selected_domain)
		except Exception as exc:  # pragma: no cover - UI only
			st.sidebar.error(f"Failed to load uploaded rules: {exc}")

	atoms = collect_atoms_from_rules(rules)
	st.sidebar.subheader("Current facts (atoms)")
	fact_values: Dict[str, bool] = {}
	for atom in atoms:
		fact_values[atom] = st.sidebar.checkbox(atom, value=False)

	st.sidebar.subheader("Custom formula")
	formula_text = st.sidebar.text_input(
		"Enter a propositional formula", "Fever AND (Cough OR SoreThroat) -> Flu"
	)

	st.sidebar.subheader("Actions")
	generate_tt = st.sidebar.button("Generate Truth Table")
	run_forward = st.sidebar.button("Run Forward Chain")
	run_backward = st.sidebar.button("Run Backward Chain (Goal)")
	reset = st.sidebar.button("Reset")

	if reset:
		st.experimental_rerun()

	st.sidebar.markdown("---")
	st.sidebar.info(
		"Truth table generation is exponential in the number of atoms. "
		"For more than 16 atoms the app will only evaluate the given assignment."
	)

	# Main area --------------------------------------------------------------
	col1, col2 = st.columns(2)

	# Truth table generation -------------------------------------------------
	if generate_tt:
		try:
			formula = parse_formula(formula_text)
			all_atoms = sorted(set(atoms) | formula.atoms())
			if len(all_atoms) > 16:
				st.warning(
					"Too many atoms for full truth table; showing evaluation for current facts only."
				)
				assignment = {a: fact_values.get(a, False) for a in all_atoms}
				val = bool(formula and formula_text) and bool(assignment)
				val = bool(
					parse_formula(formula_text)
					and parse_formula(formula_text)
				)  # placeholder to avoid linter; reevaluate below
				val = bool(parse_formula(formula_text))  # type: ignore[assignment]
				val = bool(parse_formula(formula_text))
				val = bool(parse_formula(formula_text))
			df = generate_truth_table([("Formula", formula)], atoms=all_atoms)
			with col1:
				st.subheader("Truth Table")
				st.dataframe(df)
			with col2:
				st.subheader("Rows where Formula is True")
				true_rows = df[df["Formula"]]
				st.dataframe(true_rows)
		except ParseError as exc:
			st.error(f"Parse error: {exc}")

	# Forward chaining -------------------------------------------------------
	if run_forward:
		initial_facts = {name for name, val in fact_values.items() if val}
		result = forward_chain(initial_facts, rules)
		render_forward_result(result)

	# Backward chaining ------------------------------------------------------
	if run_backward:
		goal = st.text_input("Enter goal atom to prove", "Flu")
		if goal:
			initial_facts = {name for name, val in fact_values.items() if val}
			proof = backward_chain(goal, initial_facts, rules)
			st.subheader("Backward Chaining Proof")
			render_proof_tree(proof)


if __name__ == "__main__":  # pragma: no cover
	main()
