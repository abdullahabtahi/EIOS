"""Context-aware numerical token extractor and normalizer (US5)."""

import re

from pydantic import BaseModel


class ExtractedNumber(BaseModel):
    """Extracted numeric token with position and mathematical value."""

    raw_string: str
    normalized_value: float
    start_char: int
    end_char: int


MONTH_PATTERN = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|"
    r"December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
)


class NumericTokenNormalizer:
    """Extracts numbers while excluding dates, citations, entity IDs, and list bullets."""

    def __init__(self) -> None:
        pass

    def _find_excluded_spans(self, text: str) -> list[tuple[int, int]]:
        """Identify text spans that should be excluded from numeric metric extraction."""
        spans: list[tuple[int, int]] = []

        # 1. Bracketed citations: [1], [EVID-102]
        for m in re.finditer(r"\[[A-Za-z0-9_-]+\]", text):
            spans.append(m.span())

        # 2. Dates: "March 15, 2026", "15th", or years 1900-2099
        for m in re.finditer(rf"{MONTH_PATTERN}\s+\d{{1,2}}(?:,\s+\d{{4}})?", text, re.IGNORECASE):
            spans.append(m.span())
        for m in re.finditer(r"\b\d{1,2}(?:st|nd|rd|th)\b", text, re.IGNORECASE):
            spans.append(m.span())
        for m in re.finditer(r"\b(19\d\d|20\d\d)\b", text):
            spans.append(m.span())

        # 3. Time window adjectives: "90-day", "24-hour", "7-day"
        for m in re.finditer(
            r"\b\d+-(?:day|hour|month|year|minute|second|d|h|m|s|wk)\b", text, re.IGNORECASE
        ):
            spans.append(m.span())

        # 4. Entity IDs: "Partner 8821", "Client 1001", "Case 402"
        for m in re.finditer(
            r"\b(?:Partner|Client|Account|Case|Alert|Decision|Device|IP|Product|User|Trader|"
            r"Ticket|Rule)\s+#?(\d+)\b",
            text,
            re.IGNORECASE,
        ):
            spans.append(m.span(1))

        # 4b. Hyphenated identifier codes: P-101, C-1001, TXN-1, CASE-1
        for m in re.finditer(r"\b[A-Za-z]+-\d+\b", text):
            spans.append(m.span())

        # 4c. Statutory and regulatory citations: Section 314(b), 31 CFR 1010, Form 111, Title 31
        for m in re.finditer(
            r"\b(?:\d+\s+)?(?:Section|Sec\.|CFR|USC|Article|Directive|Form|Doc|Rule|Regulation|Reg)\s+[\w\d()./-]+",
            text,
            re.IGNORECASE,
        ):
            spans.append(m.span())

        # 5. List bullets at line/sentence start: "1. ", ". 1. "
        for m in re.finditer(r"(?:^|\n|[.!?]\s+)\s*(?:#{1,6}\s*|[-*+]\s+)?(\d+)\.\s+", text):
            spans.append(m.span(1))

        # 6. Conversational structuring (Option 1, Step 2, etc.)
        for m in re.finditer(
            r"\b(?:Option|Step|Stage|Phase|Level|Tier|Part|Choice|Question|Reason|Factor)\s+#?(\d+)\b",
            text,
            re.IGNORECASE,
        ):
            spans.append(m.span(1))

        # 7. Conversational counts ("3 options", "2 reasons")
        for m in re.finditer(
            r"\b(\d+)\s+(?:options|steps|stages|phases|levels|tiers|parts|choices|questions|reasons|factors|things|metrics|components|items|areas)\b",
            text,
            re.IGNORECASE,
        ):
            spans.append(m.span(1))

        return spans

    def extract_numbers(self, text: str) -> list[ExtractedNumber]:
        """Extract all quantitative metric numbers from text."""
        excluded_spans = self._find_excluded_spans(text)
        # A k/m/b suffix counts only as a whole unit letter (1.2M, 1.2 B), never the start of a word (bps, months).
        pattern = r"([$€£]?\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s?[kKmMbB](?![A-Za-z])|\s?%)?)"
        results: list[ExtractedNumber] = []

        for m in re.finditer(pattern, text):
            span = m.span()
            raw = m.group(1).strip()

            if not raw or not any(c.isdigit() for c in raw):
                continue

            overlaps = any(max(span[0], s) < min(span[1], e) for s, e in excluded_spans)
            if overlaps:
                continue

            val = self.normalize(raw)
            if val is not None:
                results.append(
                    ExtractedNumber(
                        raw_string=raw,
                        normalized_value=val,
                        start_char=span[0],
                        end_char=span[1],
                    )
                )

        return results

    def normalize(self, raw_str: str) -> float | None:
        """Parse raw numerical string into normalized float."""
        clean = raw_str.replace("$", "").replace("€", "").replace("£", "").replace(",", "").strip()

        multiplier = 1.0
        if clean.endswith("%"):
            multiplier = 0.01
            clean = clean[:-1].strip()
        elif clean.endswith(("k", "K")):
            multiplier = 1000.0
            clean = clean[:-1].strip()
        elif clean.endswith(("m", "M")):
            multiplier = 1000000.0
            clean = clean[:-1].strip()
        elif clean.endswith(("b", "B")):
            multiplier = 1000000000.0
            clean = clean[:-1].strip()

        try:
            return float(clean) * multiplier
        except ValueError:
            return None
