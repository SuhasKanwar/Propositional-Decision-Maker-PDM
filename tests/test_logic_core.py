from __future__ import annotations

from typing import Dict

import os
import sys

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

from logic_core import (
	And,
	Atom,
	Iff,
	Implies,
	Not,
	Or,
	Xor,
	backward_chain,
	forward_chain,
	generate_truth_table,
	Rule,
	evaluate,
)
from parser import ParseError, parse_formula


def test_parser_basic_operators() -> None:
	f = parse_formula("A AND (B OR NOT C) -> D")
	assert "A" in f.atoms()
	assert "B" in f.atoms()
	assert "C" in f.atoms()
	assert "D" in f.atoms()


def test_evaluate_simple_formulas() -> None:
	a = Atom("A")
	b = Atom("B")
	formula = And(a, Not(b))
	assignment: Dict[str, bool] = {"A": True, "B": False}
	assert evaluate(formula, assignment) is True
	assignment["B"] = True
	assert evaluate(formula, assignment) is False


def test_truth_table_row_count() -> None:
	f = parse_formula("A AND B")
	df = generate_truth_table([("F", f)])
	# 2 atoms -> 4 rows
	assert len(df) == 4
	# exactly one row where both A and B are true
	true_rows = df[df["F"]]
	assert len(true_rows) == 1


def test_forward_chain_infers_conclusion() -> None:
	# A AND B -> C
	rule = Rule(
		id="R1",
		premise=parse_formula("A AND B"),
		conclusion=parse_formula("C"),
		description="If A and B then C",
	)
	result = forward_chain({"A", "B"}, [rule])
	assert "C" in result.final_facts
	assert result.steps, "At least one rule should have fired"


def test_backward_chain_proves_goal() -> None:
	# A AND B -> C, and A, B are facts
	rule = Rule(
		id="R1",
		premise=parse_formula("A AND B"),
		conclusion=parse_formula("C"),
		description="If A and B then C",
	)
	proof = backward_chain("C", {"A", "B"}, [rule])
	assert proof.succeeded is True
	assert proof.rule_id == "R1"


def test_parser_invalid_input_raises() -> None:
	try:
		parse_formula("A AND AND B")
		raised = False
	except ParseError:
		raised = True
	assert raised is True
