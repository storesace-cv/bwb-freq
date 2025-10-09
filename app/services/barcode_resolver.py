from __future__ import annotations

from collections import defaultdict
import re
from typing import (
    Dict,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)


def _is_ean13(s: str) -> bool:
    return s.isdigit() and len(s) == 13


_STORE_SPLIT_RE = re.compile(r"[;,]")
_CODE_RE = re.compile(r"\d+")


def _extract_store_tokens(value: str) -> Set[str]:
    tokens: Set[str] = set()
    if not value:
        return tokens
    for raw in _STORE_SPLIT_RE.split(value):
        token = raw.strip()
        if not token:
            continue
        tokens.add(token)
        tokens.update(match.group(0) for match in _CODE_RE.finditer(token))
    return tokens


def build_barcode_lookup(rows: Iterable[MutableMapping[str, Optional[str]]]) -> Dict[str, List[dict]]:
    """Index barcode rows by ArticleFoId for faster resolution."""

    lookup: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        article_code = (row.get("ArticleFoId") or "").strip()
        if not article_code:
            continue
        barcode_value = (row.get("Barcode") or "").strip()
        store_names = (row.get("StoreNames") or "").strip()
        lookup[article_code].append(
            {
                "Barcode": barcode_value,
                "StoreTokens": _extract_store_tokens(store_names),
            }
        )
    return lookup


def resolve_barcode(
    article_codigo: str,
    article_cod_barras: Optional[str],
    barcodes_lookup: MutableMapping[str, Sequence[dict]],
    warehouse_codigo: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve the barcode value/type for an article on a given warehouse."""

    candidates = barcodes_lookup.get(article_codigo, [])
    for candidate in candidates:
        tokens: Set[str] = candidate.get("StoreTokens", set())
        if not tokens or warehouse_codigo in tokens:
            val = candidate.get("Barcode", "")
            if val:
                return val, ("EAN13" if _is_ean13(val) else "Code128")

    for candidate in candidates:
        val = candidate.get("Barcode", "")
        if val:
            return val, ("EAN13" if _is_ean13(val) else "Code128")

    if article_cod_barras:
        val = article_cod_barras.strip()
        if val:
            return val, ("EAN13" if _is_ean13(val) else "Code128")

    return None, None
