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
	def __init__(self, text: str):
		self.tokens = tokenize(text)
		self.pos = 0

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
	parser = Parser(text)
	return parser.parse()


def formula_to_str(node: Formula) -> str:
	PRECEDENCE = {
		Atom: 7,
		Not: 6,
		And: 5,
		Xor: 4,
		Or: 3,
		Implies: 2,
		Iff: 1,
	}

	def _wrap(child: Formula, parent_prec: int) -> str:
		text = _fmt(child)
		child_prec = PRECEDENCE[type(child)]
		if child_prec < parent_prec:
			return f"({text})"
		return text

	def _fmt(n: Formula) -> str:
		if isinstance(n, Atom):
			return n.name
		if isinstance(n, Not):
			return f"NOT {_wrap(n.operand, PRECEDENCE[Not])}"
		if isinstance(n, And):
			return f"{_wrap(n.left, PRECEDENCE[And])} AND {_wrap(n.right, PRECEDENCE[And])}"
		if isinstance(n, Xor):
			return f"{_wrap(n.left, PRECEDENCE[Xor])} XOR {_wrap(n.right, PRECEDENCE[Xor])}"
		if isinstance(n, Or):
			return f"{_wrap(n.left, PRECEDENCE[Or])} OR {_wrap(n.right, PRECEDENCE[Or])}"
		if isinstance(n, Implies):
			return f"{_wrap(n.left, PRECEDENCE[Implies])} -> {_wrap(n.right, PRECEDENCE[Implies])}"
		if isinstance(n, Iff):
			return f"{_wrap(n.left, PRECEDENCE[Iff])} <-> {_wrap(n.right, PRECEDENCE[Iff])}"
		raise TypeError(f"Unsupported formula node: {type(n)!r}")

	return _fmt(node)


__all__ = [
	"ParseError",
	"Token",
	"tokenize",
	"Parser",
	"parse_formula",
	"formula_to_str",
]