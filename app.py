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
	evaluate,
	generate_truth_table,
)
from parser import ParseError, parse_formula, formula_to_str


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
	col_a, col_b = st.columns(2)
	with col_a:
		st.write("Final Facts")
		if result.final_facts:
			st.dataframe(pd.DataFrame(sorted(result.final_facts), columns=["Fact"]))
		else:
			st.info("No facts were inferred.")
	with col_b:
		st.write("Fired Rules")
		if result.steps:
			fired_df = pd.DataFrame(
				[
					{
						"Step": s.step,
						"Rule": s.rule_id,
						"Inferred": ", ".join(sorted(s.inferred)),
						"Explanation": s.explanation,
					}
					for s in result.steps
				]
			)
			st.dataframe(fired_df)
		else:
			st.info("No rules fired.")

	if result.contradictions:
		st.error("Contradictions")
		st.dataframe(
			pd.DataFrame(
				[(atom, msg) for atom, msg in result.contradictions],
				columns=["Atom", "Message"],
			)
		)


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

	if "custom_rules" not in st.session_state:
		st.session_state.custom_rules = {"medical": [], "loan": []}
	if "formula_text" not in st.session_state:
		st.session_state.formula_text = "Fever AND (Cough OR SoreThroat) -> Flu"
	if "selected_domain" not in st.session_state:
		st.session_state.selected_domain = "medical"

	st.sidebar.header("Configuration")
	st.session_state.selected_domain = st.sidebar.selectbox(
		"Rule set domain", ["medical", "loan"], index=["medical", "loan"].index(st.session_state.selected_domain)
	)

	rule_sets = load_rule_sets()
	selected_domain = st.session_state.selected_domain
	rules_base = rule_sets[selected_domain]
	rules = rules_base + st.session_state.custom_rules[selected_domain]

	uploaded = st.sidebar.file_uploader("Upload rules.json", type="json")
	if uploaded is not None:
		try:
			data = json.loads(uploaded.read().decode("utf8"))
			from logic_core import load_rules_from_json
			loaded_custom = load_rules_from_json(data, selected_domain)
			st.session_state.custom_rules[selected_domain] = loaded_custom
			st.sidebar.success("Custom rules loaded.")
		except Exception as exc:  # pragma: no cover - UI only
			st.sidebar.error(f"Failed to load uploaded rules: {exc}")

	atoms = collect_atoms_from_rules(rules)
	st.sidebar.subheader("Facts")
	fact_values: Dict[str, bool] = {}
	for atom in atoms:
		fact_values[atom] = st.sidebar.checkbox(atom, value=False)

	if st.sidebar.button("Reset State"):
		for k in ["custom_rules", "formula_text"]:
			if k == "custom_rules":
				st.session_state[k] = {"medical": [], "loan": []}
			else:
				st.session_state[k] = "Fever AND (Cough OR SoreThroat) -> Flu"
		st.rerun()

	st.sidebar.info(
		"Generate truth tables, apply forward chaining to infer new facts, or prove a goal using backward chaining."
	)

	tab_tt, tab_forward, tab_backward, tab_rules = st.tabs(
		["Truth Table", "Forward Chain", "Backward Chain", "Rules"]
	)

	with tab_tt:
		st.subheader("Truth Table & Formula Evaluation")
		builder_cols = st.columns([1, 1, 1, 1, 1, 1, 1, 1])
		buttons = ["NOT", "AND", "OR", "XOR", "->", "<->", "(", ")"]
		for col, label in zip(builder_cols, buttons):
			if col.button(label):
				append = {
					"NOT": "NOT ",
					"AND": " AND ",
					"OR": " OR ",
					"XOR": " XOR ",
					"->": " -> ",
					"<->": " <-> ",
					"(": "(",
					")": ")",
				}[label]
				st.session_state.formula_text += append
		if st.button("Clear Formula"):
			st.session_state.formula_text = ""

		formula_text = st.text_input(
			"Formula", st.session_state.formula_text, key="formula_input"
		)
		st.session_state.formula_text = formula_text

		try:
			formula = parse_formula(formula_text)
			all_atoms = sorted(set(atoms) | formula.atoms())
			mode = st.radio(
				"Evaluation Mode",
				["Full Table", "Current Assignment"],
				index=0 if len(all_atoms) <= 16 else 1,
				help="Full table enumerates all combinations; Current uses selected facts.",
			)
			if mode == "Full Table":
				if len(all_atoms) > 16:
					st.warning(
						f"Too many atoms ({len(all_atoms)}) for full table. Showing current assignment only."
					)
					mode = "Current Assignment"
			if mode == "Full Table":
				df = generate_truth_table([("Formula", formula)], atoms=all_atoms)
				st.caption(f"Rows: {len(df)} (2^{len(all_atoms)})")
				st.dataframe(df)
				true_rows = df[df["Formula"]]
				st.write("True rows")
				st.dataframe(true_rows)
			else:
				assignment = {a: fact_values.get(a, False) for a in all_atoms}
				val = generate_truth_table([("Formula", formula)], atoms=all_atoms).iloc[0]["Formula"] if len(all_atoms) == 0 else evaluate(formula, assignment)
				st.write("Current assignment:")
				st.json(assignment)
				st.metric("Formula evaluates to", str(val))
			st.success("Formula parsed successfully.")
		except ParseError as exc:
			st.error(f"Parse error: {exc}")

	with tab_forward:
		st.subheader("Forward Chaining")
		if st.button("Run Forward Chaining"):
			initial_facts = {name for name, val in fact_values.items() if val}
			result = forward_chain(initial_facts, rules)
			render_forward_result(result)
		else:
			st.info("Select facts in the sidebar and click the button to infer new facts.")

	with tab_backward:
		st.subheader("Backward Chaining")
		goal = st.text_input("Goal atom to prove", "Flu", key="goal_atom")
		if st.button("Run Backward Chaining"):
			initial_facts = {name for name, val in fact_values.items() if val}
			proof = backward_chain(goal, initial_facts, rules)
			st.subheader("Proof Tree")
			render_proof_tree(proof)
		else:
			st.info("Enter a goal atom and click the button to attempt a proof.")

	with tab_rules:
		st.subheader("Rules")
		if rules:
			rules_df = pd.DataFrame(
				[
					{
						"ID": r.id,
						"Premise": formula_to_str(r.premise),
						"Conclusion": formula_to_str(r.conclusion),
						"Text": r.description,
					}
					for r in rules
				]
			)
			st.dataframe(rules_df, width='stretch')
		else:
			st.info("No rules loaded for this domain.")

		st.markdown("### Add New Rule")
		with st.form("add_rule_form"):
			new_id = st.text_input("Rule ID", "R_new")
			premise_text = st.text_input("Premise", "Fever AND Cough")
			conclusion_text = st.text_input("Conclusion", "Flu")
			description = st.text_area("Description", "If Fever and Cough then Flu")
			submitted = st.form_submit_button("Add Rule")
			if submitted:
				try:
					premise_f = parse_formula(premise_text)
					conclusion_f = parse_formula(conclusion_text)
					st.session_state.custom_rules[selected_domain].append(
						Rule(
							id=new_id,
							premise=premise_f,
							conclusion=conclusion_f,
							description=description,
						)
					)
					st.success(f"Added rule {new_id}.")
					st.rerun()
				except ParseError as exc:
					st.error(f"Failed to parse rule formulas: {exc}")

		if st.button("Download Current Rules as JSON"):
			serialisable = {
				"domain": selected_domain,
				"rules": [
					{
						"id": r.id,
						"premise": formula_to_str(r.premise),
						"conclusion": formula_to_str(r.conclusion),
						"text": r.description,
					}
					for r in rules
				],
			}
			st.download_button(
				label="Download JSON",
				data=json.dumps(serialisable, indent=2),
				file_name=f"{selected_domain}_rules.json",
				mime="application/json",
			)


if __name__ == "__main__":
	main()