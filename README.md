# Propositional Decision Maker (PDM)

AI decision system using propositional logic, truth tables, and
rule-based inference (forward and backward chaining).

## Requirements

- Python 3.11+
- Dependencies listed in `requirements.txt`.

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Streamlit App

From the project root:

```bash
streamlit run app.py
```

## Running Tests

```bash
pytest
```

## Architecture Overview

- `parser.py` – recursive-descent parser for propositional formulas.
- `logic_core.py` – AST node types, evaluator, truth-table generator,
	forward and backward chaining, and rule utilities.
- `rules.json` – example rule sets for medical diagnosis and loan
	approval.
- `app.py` – Streamlit UI that exposes truth-table generation and
	inference (forward/backward chaining), and allows rule sets to be
	loaded from JSON.
- `tests/test_logic_core.py` – unit tests for the core logic and parser.

### Formula Syntax

Supported operators (case-insensitive):

- `NOT`, `~` – negation
- `AND`, `&` – conjunction
- `OR`, `|` – disjunction
- `XOR` – exclusive or
- `->` – implication
- `<->` – equivalence (iff)

Parentheses can be used freely to override precedence.

### Complexity Notes

Truth-table generation is exponential in the number of atoms: `O(2^n)`
rows for `n` distinct atoms. For more than 16 atoms the UI warns and
should be used in "evaluate current facts" style only.

Forward and backward chaining are roughly linear in the number of rule
applications but can increase significantly with many interdependent or
circular rules.

### Adding New Rules

Edit `rules.json` and add entries to the `medical` or `loan` arrays with
fields:

- `id` – rule identifier (e.g. `"R5"`).
- `premise` – propositional formula string.
- `conclusion` – propositional formula string (typically a single
	atom).
- `text` – human-readable explanation of the rule.

Then restart the Streamlit app or reload the page to pick up the
changes.

