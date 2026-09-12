from __future__ import annotations

import re
import unicodedata

from pypinyin import Style, lazy_pinyin
from pypinyin.contrib.tone_convert import to_tone


def is_hanzi(char: str) -> bool:
    name = unicodedata.name(char, "")
    return char == "〇" or name.startswith(("CJK UNIFIED IDEOGRAPH-", "CJK COMPATIBILITY IDEOGRAPH-"))


def normalize_pinyin(syllable: str) -> str:
    value = unicodedata.normalize("NFC", syllable.lower()).replace("u:", "ü").replace("v", "ü")
    if any(char.isdigit() for char in value):
        if not re.fullmatch(r"[a-züê]+[0-5]", value):
            raise ValueError(f"No valid pinyin: {syllable!r}; use a final tone digit from 0 to 5")
        value = to_tone(value)
    decomposed = unicodedata.normalize("NFD", value)
    if not re.fullmatch(r"[a-z\u0300\u0301\u0302\u0304\u0308\u030c]+", decomposed):
        raise ValueError(f"No valid pinyin: {syllable!r}; supply --pinyin or use --no-pinyin")
    if not any("a" <= char <= "z" for char in decomposed):
        raise ValueError(f"Invalid pinyin syllable: {syllable!r}")
    return unicodedata.normalize("NFC", value)


def parse_text(text: str, maximum: int) -> tuple[str, int, dict[int, str]]:
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    chars = []
    overrides = {}
    ignored = 0
    index = 0
    while index < len(text):
        char = text[index]
        if is_hanzi(char):
            chars.append(char)
            if index + 1 < len(text) and text[index + 1] == "[":
                end = text.find("]", index + 2)
                if end == -1:
                    raise ValueError(f"Unclosed pinyin annotation after {char!r}; use 字[zi4]")
                overrides[len(chars) - 1] = normalize_pinyin(text[index + 2 : end])
                index = end + 1
                continue
        elif char in "[]":
            raise ValueError("Pinyin annotation must immediately follow a Chinese character: 字[zi4]")
        else:
            ignored += 1
        index += 1
    if not chars:
        raise ValueError("No Chinese characters remain after cleaning the input")
    if len(chars) > maximum:
        raise ValueError(f"Input contains {len(chars)} Chinese characters; maximum is {maximum}")
    return "".join(chars), ignored, overrides


def clean_text(text: str, maximum: int) -> tuple[str, int]:
    chars, ignored, _ = parse_text(text, maximum)
    return chars, ignored


def build_pinyin(
    chars: str,
    *,
    enabled: bool,
    override: str | None,
    inline: dict[int, str] | None = None,
) -> tuple[str, ...]:
    if override is not None and not enabled:
        raise ValueError("pinyin and no_pinyin cannot be used together")
    if override is not None and inline:
        raise ValueError("--pinyin and inline pinyin annotations cannot be used together")
    if not enabled:
        return ("",) * len(chars)
    if override is not None:
        if not isinstance(override, str):
            raise ValueError("pinyin must be a space-separated string")
        syllables = override.split()
    else:
        # Preserve phrase context, then replace only the annotated occurrences.
        syllables = lazy_pinyin(chars, style=Style.TONE, v_to_u=True)
        for index, syllable in (inline or {}).items():
            syllables[index] = syllable
    if len(syllables) != len(chars):
        raise ValueError(f"Expected {len(chars)} pinyin syllables, got {len(syllables)}")
    return tuple(normalize_pinyin(syllable) for syllable in syllables)
