#!/usr/bin/env python3
"""
A robust Python lexer (extended output).

Updates from previous version:
- Token dataclass now includes start_offset (inclusive, 0-based) and end_offset (exclusive, 0-based).
- end_col is inclusive.
- Lexer has `emit_comments` option to control whether comments are returned as tokens.
- Added Token.to_dict() and Lexer.tokens_to_json() for machine-readable output.
- CLI: run without args to pretty-print tokens, use `--json` to print JSON array.
"""
from dataclasses import dataclass
import re
import ast
import json
from typing import Optional, Any, List

# --- Token dataclass ---
@dataclass
class Token:
    type: str
    lexeme: str
    value: Optional[Any]
    start_offset: int    # 0-based inclusive
    end_offset: int      # 0-based exclusive
    start_line: int      # 1-based
    start_col: int       # 1-based
    end_line: int        # 1-based
    end_col: int         # 1-based inclusive

    def to_dict(self):
        return {
            "type": self.type,
            "lexeme": self.lexeme,
            "value": self.value,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "start_line": self.start_line,
            "start_col": self.start_col,
            "end_line": self.end_line,
            "end_col": self.end_col,
        }

# --- Default keyword set (C-like subset) ---
DEFAULT_KEYWORDS = {
    "if", "else", "while", "for", "return",
    "break", "continue", "struct", "typedef", "const",
    "int", "float", "char", "void", "short", "long",
    "unsigned", "signed", "double", "static", "extern"
}

# --- Build operator/punctuation patterns ---
_MULTI_CHAR_OPS = [
    ">>=", "<<=", "==", "!=", "<=", ">=", "&&", "||", "++", "--",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<", ">>", "->", "::"
]
_MULTI_CHAR_OPS.sort(key=len, reverse=True)
multi_ops_pattern = "|".join(re.escape(op) for op in _MULTI_CHAR_OPS)

single_punct_chars = r"\+\-*/%=&|^~!<>?:;,\.\(\)\{\}\[\]"

# --- Token specification (order matters) ---
token_specification = [
    ("BLOCK_COMMENT", r"/\*[\s\S]*?\*/"),                 # block comment (can be multiline)
    ("LINE_COMMENT",  r"//[^\r\n]*"),                     # single-line comment
    ("NEWLINE",       r"\r\n|\r|\n"),                     # line breaks
    ("SKIP",          r"[ \t\f\v]+"),                     # spaces & tabs
    ("FLOAT",         r"(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?|(?:\d+[eE][+-]?\d+)"),
    ("HEX_INT",       r"0[xX][0-9a-fA-F]+"),
    ("BIN_INT",       r"0[bB][01]+"),
    ("OCT_INT",       r"0[oO][0-7]+"),
    ("INT",           r"\d+"),
    ("CHAR",          r"'([^'\\]|\\.)'"),
    ("STRING",        r'"([^"\\]|\\.)*"'),
    ("ID",            r"[A-Za-z_][A-Za-z0-9_]*"),
    ("OP",            multi_ops_pattern),
    ("PUNCT",         rf"[{single_punct_chars}]"),
    ("MISMATCH",      r"."),
]

_master_re = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in token_specification), re.MULTILINE)

# --- Helper functions ---
def _unescape_string(lit: str) -> str:
    """Safely unescape a Python-style string/char literal using ast.literal_eval."""
    return ast.literal_eval(lit)

# --- Lexer class ---
class Lexer:
    def __init__(self, code: str, keywords: Optional[set] = None, stop_on_error: bool = True, emit_comments: bool = False):
        self.code = code
        self.keywords = keywords if keywords is not None else DEFAULT_KEYWORDS
        self.stop_on_error = stop_on_error
        self.emit_comments = emit_comments

    def tokenize(self):
        """
        Generator yielding Token objects.
        - start_offset: 0-based index of first char (inclusive)
        - end_offset: 0-based index after last char (exclusive)
        - start_line/start_col: 1-based
        - end_col: inclusive (1-based)
        """
        line = 1
        line_start = 0  # index in self.code of current line start (0-based)
        for mo in _master_re.finditer(self.code):
            kind = mo.lastgroup
            text = mo.group()
            start_idx = mo.start()
            end_idx = mo.end()

            # record start position (before updating for newlines inside the token)
            start_line = line
            start_col = start_idx - line_start + 1

            # Update line and line_start if this token contains newlines
            nl_count = text.count("\n")
            if nl_count:
                line += nl_count
                last_nl = text.rfind("\n")
                # line_start becomes index of char after the last newline inside this matched text
                line_start = end_idx - (len(text) - last_nl - 1)

            end_line = line
            # end_col should be inclusive: position of last character on its line
            end_col = end_idx - line_start  # since end_idx is exclusive, this gives inclusive col

            # Skip comments/whitespace unless emit_comments is True
            if kind in ("BLOCK_COMMENT", "LINE_COMMENT"):
                if self.emit_comments:
                    tok = Token(
                        type="COMMENT",
                        lexeme=text,
                        value=text,
                        start_offset=start_idx,
                        end_offset=end_idx,
                        start_line=start_line,
                        start_col=start_col,
                        end_line=end_line,
                        end_col=end_col,
                    )
                    yield tok
                continue
            if kind == "SKIP":
                continue
            if kind == "NEWLINE":
                # already advanced line and line_start above; NEWLINE itself is not emitted by default
                continue

            # Produce token objects for other kinds
            if kind == "ID":
                if text in self.keywords:
                    tok_type = text.upper()
                    tok_value = None
                else:
                    tok_type = "ID"
                    tok_value = text
                yield Token(
                    type=tok_type,
                    lexeme=text,
                    value=tok_value,
                    start_offset=start_idx,
                    end_offset=end_idx,
                    start_line=start_line,
                    start_col=start_col,
                    end_line=end_line,
                    end_col=end_col,
                )

            elif kind in ("INT", "HEX_INT", "BIN_INT", "OCT_INT", "FLOAT"):
                try:
                    if kind == "INT":
                        val = int(text, 10)
                    elif kind == "HEX_INT":
                        val = int(text, 16)
                    elif kind == "BIN_INT":
                        val = int(text, 2)
                    elif kind == "OCT_INT":
                        val = int(text, 8)
                    else:  # FLOAT
                        val = float(text)
                except Exception:
                    val = text
                yield Token(
                    type="NUMBER",
                    lexeme=text,
                    value=val,
                    start_offset=start_idx,
                    end_offset=end_idx,
                    start_line=start_line,
                    start_col=start_col,
                    end_line=end_line,
                    end_col=end_col,
                )

            elif kind == "STRING":
                try:
                    s = _unescape_string(text)
                except Exception:
                    s = text
                yield Token(
                    type="STRING",
                    lexeme=text,
                    value=s,
                    start_offset=start_idx,
                    end_offset=end_idx,
                    start_line=start_line,
                    start_col=start_col,
                    end_line=end_line,
                    end_col=end_col,
                )

            elif kind == "CHAR":
                try:
                    c = _unescape_string(text)
                except Exception:
                    c = text
                yield Token(
                    type="CHAR",
                    lexeme=text,
                    value=c,
                    start_offset=start_idx,
                    end_offset=end_idx,
                    start_line=start_line,
                    start_col=start_col,
                    end_line=end_line,
                    end_col=end_col,
                )

            elif kind == "OP":
                yield Token(
                    type="OP",
                    lexeme=text,
                    value=text,
                    start_offset=start_idx,
                    end_offset=end_idx,
                    start_line=start_line,
                    start_col=start_col,
                    end_line=end_line,
                    end_col=end_col,
                )

            elif kind == "PUNCT":
                yield Token(
                    type="PUNCT",
                    lexeme=text,
                    value=text,
                    start_offset=start_idx,
                    end_offset=end_idx,
                    start_line=start_line,
                    start_col=start_col,
                    end_line=end_line,
                    end_col=end_col,
                )

            elif kind == "MISMATCH":
                if self.stop_on_error:
                    raise SyntaxError(f"Unexpected character {text!r} at {start_line}:{start_col}")
                else:
                    yield Token(
                        type="ERROR",
                        lexeme=text,
                        value=f"Unexpected character {text!r}",
                        start_offset=start_idx,
                        end_offset=end_idx,
                        start_line=start_line,
                        start_col=start_col,
                        end_line=end_line,
                        end_col=end_col,
                    )

    def tokenize_all(self) -> List[Token]:
        return list(self.tokenize())

    def tokens_to_json(self, pretty: bool = False) -> str:
        toks = [t.to_dict() for t in self.tokenize_all()]
        return json.dumps(toks, indent=2 if pretty else None)

# --- Simple demo / quick test ---
if __name__ == "__main__":
    import sys, argparse

    parser = argparse.ArgumentParser(description="Lexer demo")
    parser.add_argument("--json", action="store_true", help="print tokens as JSON array")
    parser.add_argument("--emit-comments", action="store_true", help="emit comments as tokens")
    parser.add_argument("file", nargs="?", help="file to lex (default: demo sample)")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            sample = f.read()
    else:
        sample = r'''
// demo: numbers, strings, comments
int main() {
    int x = 0xFF + 42;
    float y = 3.14e-2;
    char c = '\n';
    /* multi
       line */
    if (x >= 10 && y < 1.0) {
        return 0;
    }
}
'''

    lexer = Lexer(sample, stop_on_error=True, emit_comments=args.emit_comments)
    if args.json:
        print(lexer.tokens_to_json(pretty=True))
    else:
        for t in lexer.tokenize():
            print(f"{t.type:8} {t.lexeme!r:20} value={t.value!r:12}  "
                  f"[offs {t.start_offset}-{t.end_offset}) lines {t.start_line}:{t.start_col}-{t.end_line}:{t.end_col}]")
