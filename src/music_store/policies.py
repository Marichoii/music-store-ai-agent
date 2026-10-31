"""Load the store manual with page references."""

import re
from pathlib import Path

from pydantic import Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from music_store.catalog import DEFAULT_DATA_DIR
from music_store.models import Record

POLICY_NOTES = {
    "contacts": (
        "Contacts conflict: (67) 3341-4444 (pp. 1–2) versus WhatsApp "
        "(67) 3321-4500 (p. 6). Email spellings also differ; neither contact is verified."
    ),
    "installments": (
        "Sections 3 and 3.1 (p. 3) conflict. Provisionally use per-payment minima of "
        "BRL 50 for 2–3x, BRL 80 for 4–6x and BRL 100 for 7–12x. Plans below the "
        "general BRL 100 minimum require confirmation. Single payments have no floor."
    ),
    "shipping": (
        "Local freight leaves exactly BRL 500 unspecified; the pre/post-discount "
        "threshold basis is also missing (§5.1, p. 4). Other cities and large items "
        "need quotes (§5.2, p. 5). No carrier quotation or coverage lookup is connected. "
        "Delivery windows are estimates."
    ),
    "returns": (
        "Online regret: 7 calendar days from receipt (§4.1, p. 4). Preference exchanges "
        "have no explicit starting event (§4.3). Overlapping customized, final-sale and "
        "defect rules need human review, not a categorical denial. Ask for missing facts. "
        "Clearance campaigns do not establish final-sale status."
    ),
    "warranty": (
        "Store defect exchange: 30 days from purchase (§4.2, p. 4). The manual's "
        "90-day warranty starts at receipt (§8.1, p. 7). Manufacturer-specific terms "
        "require a certificate."
    ),
    "identity_and_location": (
        "Empório da Música is in Campo Grande/MS (pp. 1–2). Local shipping rules "
        "apply to its metropolitan region; do not infer coverage for other cities."
    ),
    "scope_and_actions": (
        "Only 65 product records are queryable; the manual's 300+ claim is not inventory "
        "evidence. Accessories are not sold. No order lookup, write actions or holiday "
        "calendar is connected. The assistant must not claim to have performed purchases, "
        "refunds, reservations, complaint registration, handoffs or data deletion."
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
