"""Mocked external systems for the trading examples."""

from __future__ import annotations

from typing import Any

# The exchange's listing service: ticker name -> band. "B" is suspended;
# a ticker without a band is not listed.
LISTINGS = {"Alpha Corp": "A", "Beta Corp": "B", "Delta Corp": "A"}

# The compliance (KYC) service: customer isin -> status.
KYC = {"CUST-1": "verified", "CUST-2": "pending"}

# Which fetch started when (the fetch-order example reads it).
CALLS: list[str] = []


# --8<-- [start:bands]
def fetch_bands(keys: set[str], collected: dict[str, Any], context: Any) -> dict:
    """``{isin: band}``. Reads the ticker rows, so it ``depends_on`` ticker."""
    CALLS.append("band")
    tickers = collected.get("ticker", {})
    return {
        isin: LISTINGS[tickers[isin].name]
        for isin in keys
        if isin in tickers and tickers[isin].name in LISTINGS
    }


# --8<-- [end:bands]


# --8<-- [start:kyc]
def fetch_kyc(keys: set[str], collected: dict[str, Any], context: Any) -> dict:
    """``{customer isin: status}``: needs keys only, so no depends_on."""
    CALLS.append("kyc")
    return {isin: KYC[isin] for isin in keys if isin in KYC}


# --8<-- [end:kyc]
