from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pymupdf4llm


PYEON_RE = re.compile(r"^제\s*(\d+)\s*편\s*(.*)$")
JANG_RE = re.compile(r"^제\s*(\d+)\s*장\s*(.*)$")
JEOL_RE = re.compile(r"^제\s*(\d+)\s*절\s*(.*)$")
JO_RE = re.compile(r"^(제\s*\d+\s*조(?:\s*\([^)]+\))?)")
PAGE_NUMBER_RE = re.compile(r"^(-\s*)?\d+(\s*-)?.*$")

BULLET_PREFIXES = {"-", "•", "∙", "ㆍ", "·", "*", "▶", "▶︎", "▷", "◦"}


class HanaParser:
    """Parser for 하나손해보험 자동차보험 약관 (보통약관/특별약관)."""

    def __init__(self, pdf_path: Path | str):
        self.pdf_path = Path(pdf_path)
        self.company_name = "하나"
        self.product_name = self.pdf_path.stem.split("_", 1)[1]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def parse(self) -> Dict[str, object]:
        """Parse PDF and return structured clauses."""
        markdown_text = pymupdf4llm.to_markdown(self.pdf_path)
        lines = markdown_text.split("\n")

        special_start_idx = self._find_special_start(lines)

        if special_start_idx is None:
            botong_lines = lines
            special_lines: Sequence[str] = []
        else:
            botong_lines = lines[:special_start_idx]
            special_lines = lines[special_start_idx:]

        botong_entries = self._parse_section(botong_lines, "보통약관")
        special_entries = self._parse_section(special_lines, "특별약관")

        return {
            "company": self.company_name,
            "botong_yakgwan": botong_entries,
            "special_yakgwan": special_entries,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _find_special_start(self, lines: Sequence[str]) -> Optional[int]:
        """Locate the first heading that marks the start of 특별약관."""
        keywords = {self.product_name.replace(" ", "")}
        for suffix in ("자동차보험", "자동차보험약관", "보험"):
            if suffix in self.product_name:
                keywords.add(self.product_name.replace(suffix, ""))
        keywords = {kw for kw in keywords if kw}

        for idx, raw_line in enumerate(lines):
            stripped = raw_line.strip()
            if not stripped.startswith("#"):
                continue
            if "특별약관" not in stripped:
                continue
            normalized = stripped.replace(" ", "")
            if any(kw in normalized for kw in keywords):
                return idx

        for idx, raw_line in enumerate(lines):
            stripped = raw_line.strip()
            if stripped.startswith("#") and "특별약관" in stripped:
                return idx

        return None

    def _parse_section(self, lines: Sequence[str], category: str) -> List[Dict[str, str]]:
        entries: List[Dict[str, str]] = []
        current_pyeon = ""
        current_jang = ""
        current_jeol = ""
        current_jo = ""
        current_content: List[str] = []

        def flush() -> None:
            nonlocal current_jo, current_content
            if current_jo and current_content:
                content = "\n".join(current_content).strip()
                if content:
                    entries.append(
                        {
                            "조항": self._build_hierarchy(
                                category, current_pyeon, current_jang, current_jeol, current_jo
                            ),
                            "내용": content,
                        }
                    )
            current_jo = ""
            current_content = []

        for raw_line in lines:
            cleaned = self._clean_line(raw_line)
            if cleaned is None:
                continue

            pyeon_match = PYEON_RE.match(cleaned)
            if pyeon_match:
                flush()
                current_pyeon = self._format_title("편", pyeon_match.group(1), pyeon_match.group(2))
                current_jang = ""
                current_jeol = ""
                continue

            jang_match = JANG_RE.match(cleaned)
            if jang_match:
                flush()
                current_jang = self._format_title("장", jang_match.group(1), jang_match.group(2))
                current_jeol = ""
                continue

            jeol_match = JEOL_RE.match(cleaned)
            if jeol_match:
                flush()
                current_jeol = self._format_title("절", jeol_match.group(1), jeol_match.group(2))
                continue

            jo_match = JO_RE.match(cleaned)
            if jo_match:
                flush()
                current_jo = jo_match.group(1).strip()
                remainder = cleaned[jo_match.end() :].strip()
                if remainder:
                    current_content.append(remainder)
                continue

            if current_jo:
                current_content.append(cleaned)

        flush()
        return entries

    @staticmethod
    def _clean_line(line: str) -> Optional[str]:
        stripped = line.strip()
        if not stripped:
            return None
        stripped = stripped.lstrip("#").strip()
        if not stripped:
            return None

        # Remove table rows and page markers
        if "|" in stripped:
            return None
        if PAGE_NUMBER_RE.match(stripped):
            return None

        stripped = stripped.replace("<br>", " ").replace("<br/>", " ")
        stripped = stripped.replace("\u200b", " ").replace("\xa0", " ")
        stripped = re.sub(r"\s+", " ", stripped).strip()
        while stripped and stripped[0] in BULLET_PREFIXES:
            stripped = stripped[1:].strip()

        return stripped or None

    @staticmethod
    def _format_title(unit: str, number: str, title: str) -> str:
        title = title.strip()
        return f"제{number}{unit}({title})" if title else f"제{number}{unit}"

    @staticmethod
    def _build_hierarchy(
        category: str, pyeon: str, jang: str, jeol: str, jo: str
    ) -> str:
        parts = [category]
        if pyeon:
            parts.append(pyeon)
        if jang:
            parts.append(jang)
        if jeol:
            parts.append(jeol)
        parts.append(jo)
        return ">".join(parts)


if __name__ == "__main__":
    import json
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dataset/하나/하나_개인용자동차보험.pdf")
    parser = HanaParser(target)
    parsed = parser.parse()
    summary = {
        "company": parsed["company"],
        "botong_count": len(parsed["botong_yakgwan"]),
        "special_count": len(parsed["special_yakgwan"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
