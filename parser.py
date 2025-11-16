"""Formula parser for propositional logic.

This module exposes a small recursive‑descent parser that converts
boolean formulas written in a user friendly syntax into AST nodes
defined in ``logic_core``.

Supported operators (by decreasing precedence):

* NOT / ~  (unary)
* AND / &
* XOR
* OR / |
* ->  (IMPLIES)
* <-> (IFF)

Parentheses can be used to override precedence. Operators are
case‑insensitive and can be written either as words or symbols.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from logic_core import And, Atom, Iff, Implies, Not, Or, Xor, Formula


class ParseError(ValueError):
	"""Raised when the input formula has invalid syntax."""


@dataclass
class Token:
	kind: str
	value: str


KEYWORDS = {
	"AND": "AND",
	"OR": "OR",
	"NOT": "NOT",
	"XOR": "XOR",
}


def _is_ident_char(ch: str) -> bool:
	return ch.isalnum() or ch in {"_"}


def tokenize(text: str) -> List[Token]:
	"""Convert a formula string into a list of tokens.

	The tokenizer is intentionally simple and tailored to the grammar we need.
	"""

	tokens: List[Token] = []
	i = 0
	while i < len(text):
		ch = text[i]
		if ch.isspace():
			i += 1
			continue
		if ch in "()":
			tokens.append(Token(ch, ch))
			i += 1
			continue
		# Multi-character operators first
		if text.startswith("<->", i):
			tokens.append(Token("IFF", "<->"))
			i += 3
			continue
		if text.startswith("->", i):
			tokens.append(Token("IMPLIES", "->"))
			i += 2
			continue
		if ch == "&":
			tokens.append(Token("AND", "&"))
			i += 1
			continue
		if ch == "|":
			tokens.append(Token("OR", "|"))
			i += 1
			continue
		if ch == "~":
			tokens.append(Token("NOT", "~"))
			i += 1
			continue
		# Identifier or keyword
		if _is_ident_char(ch):
			start = i
			while i < len(text) and _is_ident_char(text[i]):
				i += 1
			ident = text[start:i]
			upper = ident.upper()
			if upper in KEYWORDS:
				tokens.append(Token(KEYWORDS[upper], ident))
			else:
				tokens.append(Token("IDENT", ident))
			continue
		raise ParseError(f"Unexpected character '{ch}' at position {i}.")
	tokens.append(Token("EOF", ""))
	return tokens


class Parser:
	"""Recursive‑descent parser for propositional logic formulas."""

	def __init__(self, text: str):
		self.tokens = tokenize(text)
		self.pos = 0

	# Utility ---------------------------------------------------------------
	@property
	def current(self) -> Token:
		return self.tokens[self.pos]

	def accept(self, kind: str) -> Optional[Token]:
		if self.current.kind == kind:
			tok = self.current
			self.pos += 1
			return tok
		return None

	def expect(self, kind: str) -> Token:
		tok = self.accept(kind)
		if tok is None:
			raise ParseError(
				f"Expected {kind} but found {self.current.kind} at position {self.pos}."
			)
		return tok

	# Grammar with precedence ----------------------------------------------
	# expr       := iff
	# iff        := implies ( IFF implies )*
	# implies    := or_expr ( IMPLIES or_expr )*
	# or_expr    := xor_expr ( OR xor_expr )*
	# xor_expr   := and_expr ( XOR and_expr )*
	# and_expr   := unary ( AND unary )*
	# unary      := NOT unary | primary
	# primary    := IDENT | '(' expr ')'

	def parse(self) -> Formula:
		node = self.parse_iff()
		if self.current.kind != "EOF":
			raise ParseError(
				f"Unexpected token '{self.current.value}' after end of formula."
			)
		return node

	def parse_iff(self) -> Formula:
		node = self.parse_implies()
		while self.accept("IFF") is not None:
			right = self.parse_implies()
			node = Iff(left=node, right=right)
		return node

	def parse_implies(self) -> Formula:
		node = self.parse_or()
		while self.accept("IMPLIES") is not None:
			right = self.parse_or()
			node = Implies(left=node, right=right)
		return node

	def parse_or(self) -> Formula:
		node = self.parse_xor()
		while self.accept("OR") is not None:
			right = self.parse_xor()
			node = Or(left=node, right=right)
		return node

	def parse_xor(self) -> Formula:
		node = self.parse_and()
		while self.accept("XOR") is not None:
			right = self.parse_and()
			node = Xor(left=node, right=right)
		return node

	def parse_and(self) -> Formula:
		node = self.parse_unary()
		while self.accept("AND") is not None:
			right = self.parse_unary()
			node = And(left=node, right=right)
		return node

	def parse_unary(self) -> Formula:
		if self.accept("NOT") is not None:
			operand = self.parse_unary()
			return Not(operand=operand)
		return self.parse_primary()

	def parse_primary(self) -> Formula:
		if self.accept("(") is not None:
			node = self.parse_iff()
			self.expect(")")
			return node
		if self.current.kind == "IDENT":
			name = self.current.value
			self.pos += 1
			return Atom(name=name)
		raise ParseError(
			f"Unexpected token '{self.current.value}' where an atom or '(' was expected."
		)


def parse_formula(text: str) -> Formula:
	"""Parse *text* into an AST ``Formula``.

	This is the main entry point used by other modules.
	"""

	parser = Parser(text)
	return parser.parse()


__all__ = [
	"ParseError",
	"Token",
	"tokenize",
	"Parser",
	"parse_formula",
]
