"""
Checks incoming native-TRX transfers to our wallet address using TronGrid's
public REST API (no private key needed — we only ever read incoming
transactions, we never move funds out of this wallet programmatically).
"""
import time
import logging
import requests

import config

log = logging.getLogger("crevio.tron")

TRONGRID_URL = f"https://api.trongrid.io/v1/accounts/{config.TRX_WALLET_ADDRESS}/transactions"


def get_recent_incoming_transfers(limit: int = 50, since_ts_ms: int = None):
    """
    Returns a list of dicts: {tx_hash, amount_trx, from_address, timestamp_ms}
    for confirmed native TRX transfers *into* our wallet, newest first.
    """
    headers = {}
    if config.TRON_API_KEY:
        headers["TRON-PRO-API-KEY"] = config.TRON_API_KEY

    params = {"only_confirmed": "true", "limit": limit, "order_by": "block_timestamp,desc"}
    try:
        resp = requests.get(TRONGRID_URL, headers=headers, params=params, timeout=15)
        data = resp.json()
    except Exception as e:
        log.warning("TronGrid request failed: %s", e)
        return []

    results = []
    for tx in data.get("data", []):
        try:
            contracts = tx["raw_data"]["contract"]
            for c in contracts:
                if c.get("type") != "TransferContract":
                    continue
                value = c["parameter"]["value"]
                to_addr_hex = value.get("to_address", "")
                amount_sun = value.get("amount", 0)
                ts_ms = tx.get("block_timestamp", 0)

                if since_ts_ms and ts_ms < since_ts_ms:
                    continue

                # TronGrid returns toAddress in base58 at top level for native TRX transfers
                # Check both the top-level field and the raw contract value field
                to_address_top = tx.get("toAddress", "")
                to_address_raw = value.get("to_address", "")
                to_ok = (
                    to_address_top == config.TRX_WALLET_ADDRESS
                    or to_address_raw == config.TRX_WALLET_ADDRESS
                )
                if not to_ok:
                    continue

                results.append({
                    "tx_hash": tx.get("txID"),
                    "amount_trx": amount_sun / 1_000_000,
                    "timestamp_ms": ts_ms,
                    "from_address": tx.get("fromAddress", ""),
                })
        except (KeyError, IndexError, TypeError):
            continue

    return results
