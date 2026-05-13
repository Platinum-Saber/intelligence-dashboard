"""
Phase 1 stub — collects live USD/LKR from exchangerate-api.com.
Requires API_KEY_EXCHANGERATE in .env (Phase 2).
"""
import logging

logger = logging.getLogger(__name__)


def fetch_usd_lkr() -> float | None:
    # TODO Phase 2: implement live fetch from exchangerate-api.com / CBSL
    logger.info("[fx_collector] Live fetch not yet implemented (debug mode active)")
    return None
