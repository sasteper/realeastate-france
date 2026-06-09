"""
Similar listings finder.

Searches the cleaned IAD France dataset for listings
closest to the user's input parameters using a weighted
distance score.

Author: [Twoje Imię i Nazwisko]
License: MIT
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "iad_clean.csv"


@dataclass
class SimilarListing:
    """
    A single similar listing result.

    Attributes:
        title: Listing title from IAD France.
        price: Listed price in EUR.
        surface_m2: Property area in m².
        bedrooms: Number of bedrooms.
        dpe_class: Energy class letter.
        city: City name.
        price_per_m2: Price per m².
        url: Link to original listing.
        similarity_pct: How similar it is (100 = identical parameters).
    """
    title: str
    price: float
    surface_m2: float
    bedrooms: float
    dpe_class: str
    city: str
    price_per_m2: float
    url: str
    similarity_pct: int


class SimilarListingsFinder:
    """
    Finds similar property listings from the IAD France dataset.

    Computes a weighted distance score based on surface area,
    number of bedrooms, and estimated price, then returns
    the closest matches.

    Args:
        data_path: Path to the cleaned CSV dataset.
    """

    def __init__(self, data_path: Optional[Path] = None) -> None:
        path = Path(data_path) if data_path else _DATA_PATH
        self._df = self._load(path)
        logger.info("SimilarListingsFinder loaded %d listings", len(self._df))

    @staticmethod
    def _load(path: Path) -> pd.DataFrame:
        """Load and prepare the dataset."""
        df = pd.read_csv(path)
        # Reconstruct property_type from dummies
        df["property_type"] = "house"
        df.loc[df["type_apartment"] == True, "property_type"] = "apartment"
        df.loc[df["type_land"] == True, "property_type"] = "land"
        return df

    def find(
        self,
        surface_m2: float,
        bedrooms: int,
        property_type: str,
        price_estimate: float,
        n: int = 5,
    ) -> list[SimilarListing]:
        """
        Return the n most similar listings.

        Similarity is computed as a weighted Euclidean distance
        over normalised surface, bedroom count, and price.

        Args:
            surface_m2: Target surface area in m².
            bedrooms: Target number of bedrooms.
            property_type: 'apartment', 'house', or 'land'.
            price_estimate: Model price estimate used as reference price.
            n: Number of results to return.

        Returns:
            List of :class:`SimilarListing` sorted by similarity (best first).
        """
        df = self._df[self._df["property_type"] == property_type].copy()

        if df.empty:
            df = self._df.copy()

        # Weighted distance (lower = more similar)
        df["_surf_d"]  = (df["surface_m2"] - surface_m2).abs() / max(surface_m2, 1)
        df["_bed_d"]   = (df["bedrooms"] - bedrooms).abs() / max(bedrooms, 1)
        df["_price_d"] = (df["price"] - price_estimate).abs() / max(price_estimate, 1)
        df["_score"]   = (
            df["_surf_d"]  * 0.45 +
            df["_bed_d"]   * 0.30 +
            df["_price_d"] * 0.25
        )

        top = df.nsmallest(n, "_score")

        results = []
        for _, row in top.iterrows():
            score = float(row["_score"])
            # Convert score to similarity percentage (0 score = 100%, 1.0 score = 0%)
            sim_pct = max(0, int((1 - min(score, 1)) * 100))
            results.append(SimilarListing(
                title=str(row.get("title", ""))[:60],
                price=float(row["price"]),
                surface_m2=float(row["surface_m2"]),
                bedrooms=float(row["bedrooms"]),
                dpe_class=str(row.get("dpe_class", "—")),
                city=str(row.get("city", "—")),
                price_per_m2=float(row.get("price_per_m2", 0)),
                url=str(row.get("url", "")),
                similarity_pct=sim_pct,
            ))
        return results
