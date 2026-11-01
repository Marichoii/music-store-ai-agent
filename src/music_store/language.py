"""Choose a reply language without another model request."""

import re

from langdetect import PROFILES_DIRECTORY, DetectorFactory, LangDetectException

_factory = DetectorFactory()
_factory.seed = 0
_factory.load_profile(PROFILES_DIRECTORY)
_short_messages = {
    "hi": "en", "hello": "en", "hey": "en", "thank you": "en", "thanks": "en",
    "oi": "pt", "olá": "pt", "ola": "pt", "obrigado": "pt", "obrigada": "pt",
}
_portuguese_errors = {
    "invalid_message": "Envie uma mensagem entre 1 e 4.000 caracteres.",
    "incomplete": "Não consegui concluir a resposta. Tente novamente.",
    "tool_limit": "O limite de consultas foi atingido. Faça uma pergunta mais específica.",
    "empty_response": "O modelo não retornou uma resposta. Tente novamente.",
    "no_evidence": "Não consegui verificar as fontes da loja. Tente novamente.",
    "language": "Não consegui responder no seu idioma. Tente novamente.",
    "authentication": "Falha na autenticação do Gemini. Verifique a chave de API e o acesso.",
    "rate_limit": "O limite de uso do Gemini foi atingido. Tente novamente mais tarde.",
    "provider": "A chamada ao Gemini falhou. Verifique a chave, o modelo e a configuração.",
    "connection": "Não consegui me conectar ao Gemini. Tente novamente.",
    "internal": "Não consegui concluir o atendimento. Tente novamente.",
}


def detect_language(message: str, minimum_words: int = 2) -> str | None:
    words = re.findall(r"[^\W\d_]+", message.casefold())
    short_language = _short_messages.get(" ".join(words))
    if short_language is not None:
        return short_language
    if len(words) == 1:
        return None
    word_count = (
        len(words)
        if minimum_words == 2 and not any(character.isdigit() for character in message)
        else sum(len(word) > 1 for word in words)
    )
    if word_count < minimum_words:
        return None
    try:
        detector = _factory.create()
        if minimum_words == 2 and len(words) <= 5:
            detector.set_prior_map({"en": 0.5, "pt": 0.5})
        detector.append(message)
        language = detector.get_probabilities()[0]
    except (LangDetectException, IndexError):
        return None
    return language.lang if language.prob >= 0.9 else None


def language_instruction(language: str | None) -> str:
    if language is None:
        return ""
    name = {"en": "English", "pt": "Portuguese"}.get(language, f"language code {language}")
    return f"\nFor this turn, write your entire customer-facing answer in {name}."


def error_message(code: str, default: str, language: str | None) -> str:
    return _portuguese_errors.get(code, default) if language == "pt" else default
