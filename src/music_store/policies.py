"""Read the complete supplied policy manual without dropping pages or rewriting it."""

import re
from pathlib import Path

from pydantic import Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from music_store.catalog import DEFAULT_DATA_DIR
from music_store.models import Record

POLICY_NOTES = {
    "contacts": (
        "The cover and section 1.2 (pp. 1–2) give (67) 3341-4444; section 7 (p. 6) "
        "gives WhatsApp (67) 3321-4500. Email spellings also differ. "
        "Report the source conflict; neither contact is verified by this application."
    ),
    "installments": (
        "Section 3 (p. 3) gives a BRL 100 installment minimum, but section 3.1 permits "
        "lower detailed tiers. The application provisionally uses BRL 50 for 2–3 payments, "
        "BRL 80 for 4–6, and BRL 100 for 7–12. The BRL 50 exception is interpreted as "
        "a per-installment floor. Plans conflicting with the general minimum require "
        "store confirmation. A single credit payment is treated as non-installment."
    ),
    "shipping": (
        "Section 5.1 (p. 4) defines local freight strictly above/below BRL 500, "
        "leaving exactly BRL 500 unspecified. The pre/post-discount threshold basis is "
        "also unspecified. Ask for store confirmation when relevant. Section 5.2 (p. 5) "
        "requires destination, weight and dimensions for other cities, and large items "
        "may need individual quotes. No carrier quotation, postal coverage validation "
        "or exact arrival-date calculation is connected. Published windows are estimates."
    ),
    "returns": (
        "Online regret is described in section 4.1 (p. 4) as 7 calendar days from receipt. "
        "Section 4.3 gives 7 days for preference exchanges but no explicit starting event. "
        "Sections 4.4, 4.1 and 8 can overlap: customized/final-sale exclusions must not "
        "be turned into a categorical denial of a return or defect/warranty request. "
        "Ask missing purchase, timing, reason and condition facts, explain the supplied "
        "manual, and request human review for ambiguous cases. Do not give an independent "
        "legal opinion. A clearance campaign alone is not an explicit final-sale notice."
    ),
    "warranty": (
        "Distinguish the manual's 30-day store defect-exchange process from purchase "
        "(section 4.2, p. 4) and its 90-day warranty counted from receipt "
        "(section 8.1, p. 7). Manufacturer-specific certificates are absent; "
        "do not assign an exact manufacturer warranty to a particular product."
    ),
    "identity_and_location": (
        "The source manual describes Empório da Música in Campo Grande/MS (pp. 1–2). "
        "Keep those source facts intact. A project label or a different city in other "
        "context does not establish a replacement address or extend the manual's local "
        "shipping region. Clarify location conflicts before applying regional conditions."
    ),
    "scope_and_actions": (
        "The manual's 300+ instruments (p. 2) is not the queryable snapshot count of 65. "
        "No accessories or partner store names are supplied. The prototype has no "
        "order lookup, authenticated customer access, reservation, purchase, refund, "
        "complaint registration, human handoff or personal-data deletion capability. "
        "It can explain procedures, but must not claim to have performed those actions. "
        "No holiday or special-opening calendar is connected."
    ),
}


class PolicyError(ValueError):
    """The supplied manual cannot safely be read."""


class PolicyPage(Record):
    page: int = Field(gt=0)
    text: str = Field(min_length=1)


class PolicyBook:
    def __init__(self, pdf_path: Path = DEFAULT_DATA_DIR / "políticas_da_loja.pdf"):
        try:
            with pdf_path.open("rb") as source:
                reader = PdfReader(source)
                texts = tuple(
                    re.sub(r"\s+", " ", page.extract_text() or "").strip() for page in reader.pages
                )
        except (OSError, PdfReadError, ValueError, NotImplementedError) as exc:
            raise PolicyError(
                "Cannot read the supplied policy PDF. Restore the original file."
            ) from exc
        if not texts or any(not text for text in texts):
            raise PolicyError("The policy PDF contains an empty or unreadable text page.")
        self.source = pdf_path.name
        self.pages = tuple(PolicyPage(page=index, text=text) for index, text in enumerate(texts, 1))

    def context(self) -> dict:
        return {
            "source": self.source,
            "version": "Supplied manual v2.1, June 2025",
            "pages": [page.model_dump() for page in self.pages],
            "implementation_notes": dict(POLICY_NOTES),
        }
