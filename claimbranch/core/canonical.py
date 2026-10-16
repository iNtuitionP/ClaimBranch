"""Version-one finite JSON encoding for portable contracts.

UTF-8 NFC strings, sorted object keys, compact JSON, no floating-point numbers,
duplicate keys, normalized-key collisions, or implicit object conversion.
Manuscript/artifact bytes are hashed separately without text normalization.
"""
import hashlib
import json
import re
import unicodedata


class ContractError(ValueError):
    """Input violates the closed portable contract; no effect was produced."""


MAX_BYTES = 262_144


def bounded_text(value, name="text", limit=16_384):
    if not isinstance(value, str) or not value.strip():
        raise ContractError(name + " must be nonblank text")
    try:
        if len(value.encode("utf-8")) > limit:
            raise ContractError(name + " exceeds its UTF-8 limit")
    except UnicodeError as error:
        raise ContractError(name + " is not valid Unicode") from error
    return value


def identifier(value):
    bounded_text(value, "identifier", 128)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", value) is None:
        raise ContractError("stable IDs must be unambiguous ASCII tokens; prose may be Unicode")
    return value


def digest_text(value):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ContractError("expected lowercase SHA-256")
    return value


def integer(value, low=0, high=2**53 - 1):
    if type(value) is not int or not low <= value <= high:
        raise ContractError("integer outside contract bounds")
    return value


def _normalize(value, depth=0, *, collection_limit=128, _memo=None):
    if depth > 16:
        raise ContractError("JSON nesting limit exceeded")
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        integer(value, -(2**53 - 1))
        return value
    if isinstance(value, str):
        try:
            if len(value.encode("utf-8")) > 16_384:
                raise ContractError("JSON string limit exceeded")
        except UnicodeError as error:
            raise ContractError("invalid Unicode") from error
        return unicodedata.normalize("NFC", value)
    if type(value) in (list, tuple):
        if len(value) > collection_limit:
            raise ContractError("JSON collection limit exceeded")
        if _memo is not None:
            key=(id(value),depth)
            if key in _memo:return _memo[key]
        result=[_normalize(item, depth + 1, collection_limit=collection_limit,_memo=_memo) for item in value]
        if _memo is not None:_memo[key]=result
        return result
    if type(value) is dict:
        if len(value) > collection_limit:
            raise ContractError("JSON object limit exceeded")
        if _memo is not None:
            key=(id(value),depth)
            if key in _memo:return _memo[key]
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError("object keys must be text")
            normalized = _normalize(key, depth + 1, collection_limit=collection_limit,_memo=_memo)
            if normalized in result:
                raise ContractError("normalized object keys collide")
            result[normalized] = _normalize(item, depth + 1, collection_limit=collection_limit,_memo=_memo)
        if _memo is not None:_memo[(id(value),depth)]=result
        return result
    raise ContractError("unsupported JSON value")


def canonical_bytes(value):
    encoded = json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise ContractError("canonical JSON byte limit exceeded")
    return encoded


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def decode(raw):
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise ContractError("bounded UTF-8 bytes required")

    def pairs(items):
        result = {}
        for key, value in items:
            key = unicodedata.normalize("NFC", key)
            if key in result:
                raise ContractError("duplicate object key")
            result[key] = value
        return result

    def reject_number(_):
        raise ContractError("floating or non-finite numbers are outside the contract")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_float=reject_number, parse_constant=reject_number)
        return _normalize(value)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ContractError("invalid finite JSON") from error
