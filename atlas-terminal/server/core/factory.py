"""Factory for the v2 Data Gateway stack."""

from __future__ import annotations

from functools import lru_cache

from server.core.cache import CachedGateway
from server.core.chained_gateway import ChainedGateway
from server.core.data_gateway import DataGateway
from server.core.providers import FMPProvider, KISProvider, YahooQueryProvider, YFinanceProvider


@lru_cache(maxsize=1)
def get_data_gateway() -> DataGateway:
    """Return the process-wide gateway instance.

    Provider order is declarative: KIS can win for Korean tickers via
    ChainedGateway._order_for, while FMP remains the default first provider for
    globally listed equities when configured.
    """

    return CachedGateway(
        ChainedGateway(
            [
                FMPProvider(),
                KISProvider(),
                YahooQueryProvider(),
                YFinanceProvider(),
            ]
        )
    )
