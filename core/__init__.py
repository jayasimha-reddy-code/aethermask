"""
AetherMask Core - Deterministic, Bijective, Air-Gapped Semantic Obfuscation Engine.
"""
from __future__ import annotations

from core.engine import (
    BijectiveMap,
    EngineError,
    FidelityError,
    FidelityReport,
    MaskResult,
    OfflineIsomorphicEngine,
    RestoreResult,
    TransformConfig,
)
from core.ingest import DataIngestor, IngestError, SourceManifest
from core.ontology import DOMAIN_PROFILES, DomainProfile, get_profile, list_profiles
from core.profiler import SensitivityProfiler, TableProfile
from core.security import (
    CipherVault,
    InvalidPassphrase,
    KdfParams,
    SchemaMismatch,
    TamperedVault,
    VaultError,
)
from core.serialize import ArtifactWriter

__version__ = "2.1.0"

__all__ = [
    "DOMAIN_PROFILES",
    "ArtifactWriter",
    "BijectiveMap",
    "CipherVault",
    "DataIngestor",
    "DomainProfile",
    "EngineError",
    "FidelityError",
    "FidelityReport",
    "IngestError",
    "InvalidPassphrase",
    "KdfParams",
    "MaskResult",
    "OfflineIsomorphicEngine",
    "RestoreResult",
    "SchemaMismatch",
    "SensitivityProfiler",
    "SourceManifest",
    "TableProfile",
    "TamperedVault",
    "TransformConfig",
    "VaultError",
    "get_profile",
    "list_profiles",
]
