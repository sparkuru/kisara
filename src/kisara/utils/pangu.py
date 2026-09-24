"""Pangu-style spacing for plain CJK text and mixed half-width content.

The formatter preserves paragraph breaks and URLs. Apply it to extracted text,
not to raw Markdown or HTML markup.
"""

import re


_CJK = (
    r"\u2e80-\u2eff\u2f00-\u2fdf\u3040-\u30ff\u3100-\u312f"
    r"\u31a0-\u31bf\u3400-\u9fff\uf900-\ufaff\ua960-\ua97f"
    r"\uac00-\ud7ff"
)
_ANS = r"A-Za-z0-9@#$%&*+=/\-"
_CJK_BEFORE_ANS = re.compile(r"([{}])([{}])".format(_CJK, _ANS))
_ANS_BEFORE_CJK = re.compile(r"([{}])([{}])".format(_ANS, _CJK))
_CJK_BEFORE_BRACKET = re.compile(r"([{}])(\()".format(_CJK))
_BRACKET_BEFORE_CJK = re.compile(r"(\))([{}])".format(_CJK))
_URL = re.compile(r"https?://[^\s<>\"']+")
_CJK_LAST = re.compile(r"[{}]$".format(_CJK))


def pangu(text: str) -> str:
    """Add readable spacing around CJK and half-width text in plain prose.

    Existing spaces and line breaks remain intact. URL spans are preserved so
    a path containing CJK characters stays usable. This intentionally avoids
    interpreting Markdown or HTML markup.
    """

    def space_part(part: str) -> str:
        """Apply spacing rules to a span without URL syntax."""

        part = _CJK_BEFORE_ANS.sub(r"\1 \2", part)
        part = _ANS_BEFORE_CJK.sub(r"\1 \2", part)
        part = _CJK_BEFORE_BRACKET.sub(r"\1 \2", part)
        return _BRACKET_BEFORE_CJK.sub(r"\1 \2", part)

    pieces = []
    cursor = 0
    for match in _URL.finditer(text):
        before = space_part(text[cursor:match.start()])
        if before and _CJK_LAST.search(before):
            before += " "
        pieces.extend((before, match.group()))
        cursor = match.end()
    pieces.append(space_part(text[cursor:]))
    return "".join(pieces)
