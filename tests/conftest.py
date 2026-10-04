"""
AetherMask test fixtures and configuration for pytest.
"""
from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import polars as pl
import pytest

from core.ingest import DataIngestor

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")


@pytest.fixture(scope="session")
def ingestor() -> DataIngestor:
    return DataIngestor()


@pytest.fixture(scope="session")
def missions(ingestor: DataIngestor) -> pl.DataFrame:
    path = os.path.join(SAMPLES_DIR, "classified_missions.csv")
    return ingestor.load_path(path).primary


@pytest.fixture(scope="session")
def bases(ingestor: DataIngestor) -> pl.DataFrame:
    path = os.path.join(SAMPLES_DIR, "classified_bases.csv")
    return ingestor.load_path(path).primary


@pytest.fixture(scope="session")
def personnel(ingestor: DataIngestor) -> pl.DataFrame:
    path = os.path.join(SAMPLES_DIR, "classified_personnel.csv")
    return ingestor.load_path(path).primary


@pytest.fixture(scope="session")
def tables(
    missions: pl.DataFrame,
    bases: pl.DataFrame,
    personnel: pl.DataFrame,
) -> dict[str, pl.DataFrame]:
    return {"missions": missions, "bases": bases, "personnel": personnel}
