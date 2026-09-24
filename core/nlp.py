"""
AetherMask (CipherShift) :: core.nlp
====================================
Offline, deterministic Named Entity Recognition and tokenisation.

Execution model
---------------
1. **Rule-based backbone (always on, zero dependencies).** Compiled regex
   gazetteer from `core.ontology.NER_PATTERNS`, resolved by a
   longest-match / highest-priority span arbitration pass. This is fully
   deterministic and reproducible on any air-gapped host.

2. **Optional local statistical layer.** If a spaCy model (e.g. an
   `en_core_web_sm` wheel pre-installed into the offline image) or a local
   ONNX/FastEmbed model directory is present, it is loaded from disk and used
   ONLY to propose *additional* spans that the rules missed. Model loading is
   strictly local-filesystem; `spacy.load` is never given a name that would
   trigger a download, and no `spacy.cli.download` path exists in this module.

3. Statistical spans never override rule spans, so enabling or disabling the
   optional model can only ever *add* protection - it can never change an
   existing mapping. That property keeps `.ciphermap` files portable between
   a minimal appliance and a full-fat image.

No module-level side effects perform I/O beyond regex compilation. The spaCy
probe is lazy and failure-tolerant.
"""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .ontology import NER_LABEL_TO_POOL, NER_PATTERNS

__all__ = [
    "Entity",
    "OfflineNER",
    "tokenize",
    "normalise_identifier",
    "split_identifier",
    "rejoin_identifier",
]


# --------------------------------------------------------------------------- #
#  Identifier tokenisation helpers (for column headers)
# --------------------------------------------------------------------------- #
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SEPARATORS = re.compile(r"[\s_\-./\\:|]+")
_NON_WORD = re.compile(r"[^0-9A-Za-z]+")


def split_identifier(name: str) -> Tuple[List[str], List[str]]:
    """
    Split a column identifier into (tokens, separators) preserving the exact
    original delimiters so the name can be losslessly reassembled.

        "TargetLat_Deg" -> (["Target", "Lat", "Deg"], ["", "_", ""])

    The separator list has the same length as tokens; element *i* is the
    delimiter that PRECEDED token *i* ("" for the first token).
    """
    if not name:
        return [], []

    # First split on explicit separators, recording them.
    parts: List[str] = []
    seps: List[str] = []
    pos = 0
    last_end = 0
    for m in _SEPARATORS.finditer(name):
        chunk = name[last_end:m.start()]
        if chunk:
            parts.append(chunk)
            seps.append(name[pos:last_end] if pos != last_end else "")
        pos = m.start()
        last_end = m.end()
        if chunk:
            seps[-1] = name[:0] if len(seps) == 1 and m.start() == 0 else seps[-1]
    tail = name[last_end:]
    if tail:
        parts.append(tail)
        seps.append("")

    # Rebuild separators accurately via a second pass.
    tokens: List[str] = []
    separators: List[str] = []
    idx = 0
    buf_sep = ""
    while idx < len(name):
        m = _SEPARATORS.match(name, idx)
        if m:
            buf_sep += m.group(0)
            idx = m.end()
            continue
        nxt = _SEPARATORS.search(name, idx)
        end = nxt.start() if nxt else len(name)
        chunk = name[idx:end]
        # Sub-split camelCase inside the chunk.
        sub = _CAMEL_BOUNDARY.split(chunk) if chunk else []
        for j, s in enumerate(sub):
            if not s:
                continue
            tokens.append(s)
            separators.append(buf_sep if j == 0 else "")
            buf_sep = ""
        idx = end
    if not tokens:
        return [name], [""]
    return tokens, separators


def rejoin_identifier(tokens: Sequence[str], separators: Sequence[str]) -> str:
    """Inverse of :func:`split_identifier`."""
    out: List[str] = []
    for i, tok in enumerate(tokens):
        out.append(separators[i] if i < len(separators) else "")
        out.append(tok)
    return "".join(out)


def normalise_identifier(name: str) -> str:
    """Lowercase, separator-normalised form used for ontology lookups."""
    tokens, _ = split_identifier(name)
    return "_".join(t.lower() for t in tokens if t)


def tokenize(text: str) -> List[str]:
    """Deterministic whitespace/punctuation tokenizer (offline, no models)."""
    return [t for t in _NON_WORD.split(text) if t]


# --------------------------------------------------------------------------- #
#  Entity representation
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Entity:
    """A recognised span inside a free-text value."""

    text: str
    label: str
    start: int
    end: int
    priority: int
    source: str = "rule"

    @property
    def pool(self) -> str:
        return NER_LABEL_TO_POOL.get(self.label, "GENERIC")


# --------------------------------------------------------------------------- #
#  OfflineNER
# --------------------------------------------------------------------------- #
class OfflineNER:
    """
    Deterministic offline entity recogniser.

    Parameters
    ----------
    enable_statistical : attempt to load a locally-installed spaCy pipeline.
    spacy_model_path   : explicit filesystem path to a spaCy model directory.
                         If None, the env var AETHERMASK_SPACY_MODEL is used,
                         then a bare local `en_core_web_sm` import is attempted.
    """

    _STATISTICAL_LABELS = {
        "PERSON": "PERSON",
        "ORG": "ORG",
        "GPE": "PLACE",
        "LOC": "PLACE",
        "FAC": "SITE",
        "NORP": "ORG",
        "PRODUCT": "ASSET",
        "EVENT": "PROJECT",
        "WORK_OF_ART": "PROJECT",
    }

    def __init__(
        self,
        enable_statistical: bool = True,
        spacy_model_path: Optional[str] = None,
    ) -> None:
        self._compiled: List[Tuple[re.Pattern[str], str, int]] = []
        for spec in NER_PATTERNS:
            self._compiled.append(
                (
                    re.compile(str(spec["pattern"])),
                    str(spec["label"]),
                    int(spec["priority"]),  # type: ignore[arg-type]
                )
            )
        # Highest priority first => arbitration is order-independent.
        self._compiled.sort(key=lambda t: -t[2])

        self._enable_statistical = enable_statistical
        self._spacy_model_path = spacy_model_path or os.environ.get(
            "AETHERMASK_SPACY_MODEL"
        )
        self._nlp = None
        self._nlp_tried = False
        self._nlp_lock = threading.Lock()
        self._backend = "rule-based"

    # ------------------------------------------------------------------ #
    #  Optional local statistical pipeline
    # ------------------------------------------------------------------ #
    def _load_statistical(self) -> None:
        """
        Load spaCy strictly from the local filesystem. Never downloads.
        Any failure degrades silently to the rule-based backbone.
        """
        if self._nlp_tried:
            return
        with self._nlp_lock:
            if self._nlp_tried:
                return
            self._nlp_tried = True
            if not self._enable_statistical:
                return
            # Hard offline guards for any library that might probe the network.
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            os.environ.setdefault("NO_PROXY", "*")
            try:
                import spacy  # type: ignore

                if self._spacy_model_path and os.path.isdir(self._spacy_model_path):
                    self._nlp = spacy.load(
                        self._spacy_model_path, disable=["lemmatizer", "textcat"]
                    )
                    self._backend = f"rule-based + spacy({self._spacy_model_path})"
                    return
                # Locally installed wheel (no network fetch is performed by load()).
                import importlib.util

                if importlib.util.find_spec("en_core_web_sm") is not None:
                    self._nlp = spacy.load(
                        "en_core_web_sm", disable=["lemmatizer", "textcat"]
                    )
                    self._backend = "rule-based + spacy(en_core_web_sm)"
            except Exception:
                self._nlp = None  # stay on the deterministic backbone

    @property
    def backend(self) -> str:
        self._load_statistical()
        return self._backend

    # ------------------------------------------------------------------ #
    #  Recognition
    # ------------------------------------------------------------------ #
    def extract(self, text: str) -> List[Entity]:
        """
        Return non-overlapping entities sorted by start offset.

        Arbitration: higher `priority` wins; ties break on longer span; further
        ties break on earlier start. Fully deterministic.
        """
        if not text or not isinstance(text, str):
            return []

        candidates: List[Entity] = []
        for pattern, label, priority in self._compiled:
            for m in pattern.finditer(text):
                span = m.group(0)
                if not span.strip():
                    continue
                candidates.append(
                    Entity(
                        text=span, label=label, start=m.start(),
                        end=m.end(), priority=priority, source="rule",
                    )
                )

        if self._enable_statistical:
            self._load_statistical()
            if self._nlp is not None:
                try:
                    doc = self._nlp(text)
                    for ent in doc.ents:
                        mapped = self._STATISTICAL_LABELS.get(ent.label_)
                        if mapped is None:
                            continue
                        candidates.append(
                            Entity(
                                text=ent.text, label=mapped,
                                start=ent.start_char, end=ent.end_char,
                                priority=5,  # always below every rule priority
                                source="spacy",
                            )
                        )
                except Exception:
                    pass

        return self._resolve_overlaps(candidates)

    @staticmethod
    def _resolve_overlaps(cands: Iterable[Entity]) -> List[Entity]:
        ordered = sorted(
            cands, key=lambda e: (-e.priority, -(e.end - e.start), e.start, e.label)
        )
        taken: List[Entity] = []
        occupied: List[Tuple[int, int]] = []
        for ent in ordered:
            if any(ent.start < e and ent.end > s for s, e in occupied):
                continue
            taken.append(ent)
            occupied.append((ent.start, ent.end))
        return sorted(taken, key=lambda e: e.start)

    # ------------------------------------------------------------------ #
    #  Rewriting
    # ------------------------------------------------------------------ #
    def rewrite(self, text: str, resolver) -> Tuple[str, List[Entity]]:
        """
        Replace every recognised entity using `resolver(entity) -> str`.

        Reconstruction walks spans right-to-left so offsets stay valid, and the
        surrounding narrative text is preserved byte-for-byte.
        """
        ents = self.extract(text)
        if not ents:
            return text, []
        out = text
        for ent in sorted(ents, key=lambda e: -e.start):
            replacement = resolver(ent)
            out = out[: ent.start] + replacement + out[ent.end:]
        return out, ents

    def describe(self) -> Dict[str, object]:
        """Diagnostics for the air-gap attestation panel."""
        return {
            "backend": self.backend,
            "rule_patterns": len(self._compiled),
            "labels": sorted({lbl for _, lbl, _ in self._compiled}),
            "statistical_enabled": self._enable_statistical,
            "statistical_loaded": self._nlp is not None,
            "network_access": "none",
        }
