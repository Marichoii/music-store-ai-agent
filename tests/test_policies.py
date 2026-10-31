import hashlib

import pytest
from pypdf import PdfReader, PdfWriter

from music_store.catalog import DEFAULT_DATA_DIR
from music_store.policies import PolicyBook, PolicyError


@pytest.fixture(scope="module")
def policies():
    return PolicyBook()


def test_all_eight_pages_and_their_numbers_are_preserved(policies):
    context = policies.context()
    assert context["source"] == "políticas_da_loja.pdf"
    assert "2.1" in context["version"]
    assert len(context["pages"]) == 8
    assert [page["page"] for page in context["pages"]] == list(range(1, 9))
    assert all(page["text"] for page in context["pages"])


@pytest.mark.parametrize(
    "number,expected",
    [
        (2, "09:00 às 18:00"),
        (3, "3.1 Regras de Parcelamento"),
        (4, "7 (sete) dias corridos após o recebimento"),
        (5, "5 a 12 dias úteis"),
        (6, "6.2 Regras de Promoções"),
        (7, "90 (noventa) dias"),
        (8, "consentimento explícito"),
    ],
)
def test_customer_questions_have_complete_page_evidence(policies, number, expected):
    assert expected in policies.pages[number - 1].text


def test_source_location_and_conflicting_contacts_are_not_rewritten(policies):
    pages = policies.pages
    assert "Campo Grande" in pages[1].text
    assert "3341" in pages[1].text
    assert "3321-4500" in pages[5].text
    notes = policies.context()["implementation_notes"]
    assert "neither contact is verified" in notes["contacts"]
    assert "Clarify location conflicts" in notes["identity_and_location"]


def test_policy_gaps_and_unsupported_actions_are_explicit(policies):
    notes = policies.context()["implementation_notes"]
    assert "exactly BRL 500 unspecified" in notes["shipping"]
    assert "pre/post-discount" in notes["shipping"]
    assert "no explicit starting event" in notes["returns"]
    assert "categorical denial" in notes["returns"]
    assert "90-day warranty" in notes["warranty"]
    assert "must not claim to have performed" in notes["scope_and_actions"]


def test_context_mutations_do_not_change_future_policy_reads(policies):
    context = policies.context()
    context["pages"][0]["text"] = "Modified by a caller"
    context["implementation_notes"]["shipping"] = "Invented free shipping"
    fresh = policies.context()
    assert fresh["pages"][0]["text"] != "Modified by a caller"
    assert "exactly BRL 500 unspecified" in fresh["implementation_notes"]["shipping"]


def test_reading_policies_does_not_modify_the_original_pdf():
    source = DEFAULT_DATA_DIR / "políticas_da_loja.pdf"
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    PolicyBook(source).context()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_missing_pdf_has_an_actionable_error(tmp_path):
    with pytest.raises(PolicyError, match="Restore the original"):
        PolicyBook(tmp_path / "missing.pdf")


def test_corrupt_pdf_is_not_treated_as_policy_text(tmp_path):
    source = tmp_path / "invalid.pdf"
    source.write_bytes(b"not a PDF")
    with pytest.raises(PolicyError):
        PolicyBook(source)


def test_empty_or_image_only_pages_require_readable_text(tmp_path):
    source = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(source)
    with pytest.raises(PolicyError, match="empty or unreadable"):
        PolicyBook(source)


def test_encrypted_pdf_does_not_produce_unverified_context(tmp_path):
    source = tmp_path / "encrypted.pdf"
    reader = PdfReader(DEFAULT_DATA_DIR / "políticas_da_loja.pdf")
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.encrypt("test-password")
    writer.write(source)
    with pytest.raises(PolicyError):
        PolicyBook(source)
