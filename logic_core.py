from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

import pandas as pd


class Formula:
	def atoms(self) -> Set[str]:
		raise NotImplementedError


@dataclass(frozen=True)
class Atom(Formula):
	name: str

	def atoms(self) -> Set[str]:
		return {self.name}


@dataclass(frozen=True)
class Not(Formula):
	operand: Formula

	def atoms(self) -> Set[str]:
		return self.operand.atoms()


@dataclass(frozen=True)
class And(Formula):
	left: Formula
	right: Formula

	def atoms(self) -> Set[str]:
		return self.left.atoms() | self.right.atoms()


@dataclass(frozen=True)
class Or(Formula):
	left: Formula
	right: Formula

	def atoms(self) -> Set[str]:
		return self.left.atoms() | self.right.atoms()


@dataclass(frozen=True)
class Xor(Formula):
	left: Formula
	right: Formula

	def atoms(self) -> Set[str]:
		return self.left.atoms() | self.right.atoms()


@dataclass(frozen=True)
class Implies(Formula):
	left: Formula
	right: Formula

	def atoms(self) -> Set[str]:
		return self.left.atoms() | self.right.atoms()


@dataclass(frozen=True)
class Iff(Formula):
	left: Formula
	right: Formula

	def atoms(self) -> Set[str]:
		return self.left.atoms() | self.right.atoms()


FormulaLike = Formula


def evaluate(formula: FormulaLike, assignment: Dict[str, bool]) -> bool:
	if isinstance(formula, Atom):
		return bool(assignment.get(formula.name, False))
	if isinstance(formula, Not):
		return not evaluate(formula.operand, assignment)
	if isinstance(formula, And):
		return evaluate(formula.left, assignment) and evaluate(
			formula.right, assignment
		)
	if isinstance(formula, Or):
		return evaluate(formula.left, assignment) or evaluate(
			formula.right, assignment
		)
	if isinstance(formula, Xor):
		return evaluate(formula.left, assignment) ^ evaluate(
			formula.right, assignment
		)
	if isinstance(formula, Implies):
		left_val = evaluate(formula.left, assignment)
		right_val = evaluate(formula.right, assignment)
		return (not left_val) or right_val
	if isinstance(formula, Iff):
		left_val = evaluate(formula.left, assignment)
		right_val = evaluate(formula.right, assignment)
		return left_val == right_val
	raise TypeError(f"Unsupported formula type: {type(formula)!r}")


def generate_truth_table(
	formulas: Sequence[Tuple[str, FormulaLike]] | None = None,
	atoms: Optional[Sequence[str]] = None,
	filter_formula: Optional[Tuple[str, FormulaLike]] = None,
) -> pd.DataFrame:
	formulas = list(formulas or [])

	inferred_atoms: Set[str] = set()
	for _name, f in formulas:
		inferred_atoms |= f.atoms()
	if atoms is not None:
		atom_list = list(dict.fromkeys(atoms))
	else:
		atom_list = sorted(inferred_atoms)

	rows: List[Dict[str, Union[bool, str]]] = []
	for values in product([False, True], repeat=len(atom_list)):
		assignment = dict(zip(atom_list, values))
		row: Dict[str, Union[bool, str]] = {a: assignment[a] for a in atom_list}
		for name, f in formulas:
			row[name] = evaluate(f, assignment)
		if filter_formula is not None:
			fname, ff = filter_formula
			if not evaluate(ff, assignment):
				continue
			row[fname] = True
		rows.append(row)

	return pd.DataFrame(rows)


@dataclass
class Rule:
	id: str
	premise: FormulaLike
	conclusion: FormulaLike
	description: str

	def conclusion_atoms(self) -> Set[str]:
		return self.conclusion.atoms()


def load_rules_from_json(data: Dict[str, List[Dict[str, str]]], domain: str) -> List[Rule]:
	from parser import parse_formula

	raw_rules = data.get(domain, [])
	rules: List[Rule] = []
	for r in raw_rules:
		rules.append(
			Rule(
				id=r["id"],
				premise=parse_formula(r["premise"]),
				conclusion=parse_formula(r["conclusion"]),
				description=r["text"],
			)
		)
	return rules


def rules_to_json_serialisable(rules: Iterable[Rule]) -> Dict[str, List[Dict[str, str]]]:

	from parser import formula_to_str
	return {
		"rules": [
			{
				"id": r.id,
				"premise": formula_to_str(r.premise),
				"conclusion": formula_to_str(r.conclusion),
				"text": r.description,
			}
			for r in rules
		]
	}

@dataclass
class ForwardStep:
	step: int
	rule_id: str
	inferred: Set[str]
	explanation: str


@dataclass
class ForwardResult:
	final_facts: Set[str]
	steps: List[ForwardStep]
	contradictions: List[Tuple[str, str]]


def _formula_to_atoms(formula: FormulaLike, assignment: Dict[str, bool]) -> Set[str]:
	atoms = formula.atoms()
	newly_true: Set[str] = set()
	for a in atoms:
		test_assignment = dict(assignment)
		test_assignment[a] = True
		if evaluate(formula, test_assignment):
			newly_true.add(a)
	return newly_true


def detect_contradictions(facts: Set[str]) -> List[Tuple[str, str]]:
	positives: Set[str] = {f for f in facts if not f.startswith("NOT ")}
	negatives: Set[str] = {f[4:] for f in facts if f.startswith("NOT ")}
	conflicts = sorted(positives & negatives)
	return [(c, f"Contradiction between {c} and NOT {c}") for c in conflicts]


def forward_chain(initial_facts: Set[str], rules: Sequence[Rule]) -> ForwardResult:
	facts: Set[str] = set(initial_facts)
	steps: List[ForwardStep] = []
	step_counter = 1

	while True:
		fired_any = False
		for rule in rules:
			assignment = {a: (a in facts) for a in rule.premise.atoms()}
			if evaluate(rule.premise, assignment):
				new_atoms = _formula_to_atoms(rule.conclusion, assignment)
				new_atoms -= facts
				if not new_atoms:
					continue
				fired_any = True
				facts |= new_atoms
				explanation_atoms = " and ".join(sorted(rule.premise.atoms()))
				explanation = (
					f"Step {step_counter}: {rule.id} fired because "
					f"{explanation_atoms} are True -> inferred {', '.join(sorted(new_atoms))}."
				)
				steps.append(
					ForwardStep(
						step=step_counter,
						rule_id=rule.id,
						inferred=new_atoms,
						explanation=explanation,
					)
				)
				step_counter += 1
		if not fired_any:
			break

	contradictions = detect_contradictions(facts)
	return ForwardResult(final_facts=facts, steps=steps, contradictions=contradictions)

@dataclass
class ProofNode:
	goal: str
	rule_id: Optional[str]
	premises: List["ProofNode"]
	succeeded: bool
	message: str


def backward_chain(
	goal: str,
	facts: Set[str],
	rules: Sequence[Rule],
	visited: Optional[Set[str]] = None,
) -> ProofNode:

	if visited is None:
		visited = set()
	if goal in facts:
		return ProofNode(goal=goal, rule_id=None, premises=[], succeeded=True, message="Given as a fact.")
	if goal in visited:
		return ProofNode(
			goal=goal,
			rule_id=None,
			premises=[],
			succeeded=False,
			message="Cycle detected while proving this goal.",
		)
	visited.add(goal)

	applicable_rules = [r for r in rules if goal in r.conclusion_atoms()]
	if not applicable_rules:
		return ProofNode(
			goal=goal,
			rule_id=None,
			premises=[],
			succeeded=False,
			message="No rules conclude this goal.",
		)

	for rule in applicable_rules:
		sub_nodes: List[ProofNode] = []
		all_ok = True
		for atom in sorted(rule.premise.atoms()):
			node = backward_chain(atom, facts, rules, visited)
			sub_nodes.append(node)
			if not node.succeeded:
				all_ok = False
		if all_ok:
			return ProofNode(
				goal=goal,
				rule_id=rule.id,
				premises=sub_nodes,
				succeeded=True,
				message=f"Proved {goal} using rule {rule.id}.",
			)

	return ProofNode(
		goal=goal,
		rule_id=None,
		premises=[],
		succeeded=False,
		message="All applicable rules failed to prove this goal.",
	)


__all__ = [
	"Formula",
	"Atom",
	"Not",
	"And",
	"Or",
	"Xor",
	"Implies",
	"Iff",
	"evaluate",
	"generate_truth_table",
	"Rule",
	"ForwardResult",
	"ForwardStep",
	"forward_chain",
	"ProofNode",
	"backward_chain",
	"detect_contradictions",
]