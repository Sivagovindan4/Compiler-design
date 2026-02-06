#!/usr/bin/env python3
"""
Tiny lexer (Option A)

Usage:
    python tiny_lexer_a.py

This prints tokens for a small sample. Import and use `tokenize(code)` in your own code.
"""
import re
import ast
from collections import namedtuple

Token = namedtuple("Token", ["type", "value", "line", "col"])

# Keywords for the tiny language
KEYWORDS = {"if", "else", "while", "for", "return"}

# Token specification: order matters for resolution (multi-char ops before single-char).
token_spec = [
    ("COMMENT", r"//[^\n]*"),                                 # line comment
    ("NUMBER",  r"\d+(\.\d+)?"),                              # integer or decimal
    ("ID",      r"[A-Za-z_][A-Za-z0-9_]*"),                   # identifiers
    ("STRING",  r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\""),       # single or double quoted
    ("EQ",      r"=="),
    ("NE",      r"!="),
    ("LE",      r"<="),
    ("GE",      r">="),
    ("PLUS",    r"\+"),
    ("MINUS",   r"-"),
    ("TIMES",   r"\*"),
    ("DIVIDE",  r"/"),
    ("MOD",     r"%"),
    ("ASSIGN",  r"="),
    ("LT",      r"<"),
    ("GT",      r">"),
    ("LPAREN",  r"\("),
    ("RPAREN",  r"\)"),
    ("LBRACE",  r"\{"),
    ("RBRACE",  r"\}"),
    ("COMMA",   r","),
    ("SEMI",    r";"),
    ("NEWLINE", r"\n"),
    ("SKIP",    r"[ \t]+"),                                   # spaces and tabs
    ("MISMATCH",r"."),                                        # any other single char (error)
]

master_pattern = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in token_spec))

def _unescape_string(lit):
    """Convert a quoted string literal to its Python value (handles escapes).
       Returns the unquoted/unescaped string or raises ValueError if invalid."""
    return ast.literal_eval(lit)

def tokenize(code):
    """Yield tokens as Token(type, value, line, col)."""
    line = 1
    line_start = 0
    for mo in master_pattern.finditer(code):
        kind = mo.lastgroup
        text = mo.group()
        col = mo.start() - line_start + 1

        if kind == "NUMBER":
            value = float(text) if "." in text else int(text)
            yield Token("NUMBER", value, line, col)
        elif kind == "ID":
            if text in KEYWORDS:
                yield Token(text.upper(), text, line, col)  # e.g., IF
            else:
                yield Token("ID", text, line, col)
        elif kind == "STRING":
            try:
                s = _unescape_string(text)
            except Exception:
                # If literal_eval fails, return raw text as error-like string value
                s = text
            yield Token("STRING", s, line, col)
        elif kind == "COMMENT" or kind == "SKIP":
            continue
        elif kind == "NEWLINE":
            line += 1
            line_start = mo.end()
        elif kind == "MISMATCH":
            raise SyntaxError(f"Unexpected character {text!r} at {line}:{col}")
        else:
            # Operators and punctuation: return token type and the raw lexeme
            yield Token(kind, text, line, col)

# Simple demo when run as script
if __name__ == "__main__":
    sample = '''
// sample tiny program
if x == 42 {
    y = x + 3.14;
    return "ok";
}
'''
    for tok in tokenize(sample):
        print(tok)