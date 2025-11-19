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

### UI Flow (Tabs)

The application uses a tabbed layout for a clearer workflow:

- Truth Table: Build formulas using helper buttons (NOT, AND, OR, XOR, ->, <->) and either generate a full truth table (≤16 atoms) or evaluate against the current fact assignment. Shows rows where the formula is true.
- Forward Chain: Select facts in the sidebar and infer new facts. Fired rules, inferred facts, and contradictions are displayed in structured tables.
- Backward Chain: Enter a goal atom and attempt to prove it from current facts and rules. An expandable proof tree shows the reasoning path.
- Rules: Inspect all loaded rules (base + custom), add new rules via a form, or download the full domain rule set as JSON for reuse.

### Adding Rules at Runtime

Use the Rules tab form:
1. Fill in ID, premise, conclusion, and description.
2. Formulas are validated immediately; parse errors are shown inline.
3. On success, the rule is added to session state and available to chaining.

You can also upload a `rules.json` file (matching the existing schema) via the sidebar to replace the custom rules for the selected domain.

### Exporting Rules

Click "Download Current Rules as JSON" on the Rules tab to export the combined base and custom rules for the active domain.

### Resetting State

Use the sidebar "Reset State" button to clear custom rules and restore the default demo formula.

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

The UI helper buttons append tokens to the current formula. Use Clear Formula to start over quickly.

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

