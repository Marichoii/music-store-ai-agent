import pytest

from music_store.language import detect_language


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Quais violões vocês têm disponíveis?", "pt"),
        ("E aos sábados?", "pt"),
        ("What are your opening hours?", "en"),
        ("And what about Sundays?", "en"),
        ("Will local delivery be free for an order totaling exactly R$500?", "en"),
        ("Je cherche une guitare acoustique pour débutant.", "fr"),
        ("Estoy buscando una guitarra acústica para principiantes.", "es"),
        ("Hello!", "en"),
        ("Oi!", "pt"),
        ("Quanto custa?", "pt"),
        ("Tem estoque?", "pt"),
        ("E parcelado?", "pt"),
        ("Obrigado!", "pt"),
        ("How much?", "en"),
        ("In stock?", "en"),
        ("And is it available?", "en"),
        ("Is it available?", "en"),
        ("E está disponível?", "pt"),
        ("Any guitars under R$700?", "en"),
        ("PIX?", None),
        ("R$500?", None),
        ("Yamaha C40", None),
        ("83", None),
    ],
)
def test_language_detection_handles_switches_and_neutral_follow_ups(message, expected):
    assert detect_language(message) == expected
