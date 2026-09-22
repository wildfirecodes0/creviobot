"""
Wrapper around Edesy's Number Masking API.

NOTE: Edesy's exact endpoint paths/field names were not confirmed during
planning (only their pricing — Rs 1.50/min combined for both legs — was
confirmed with their support over WhatsApp). The functions below follow
the common "click-to-call bridge" pattern used by this category of API
(create a masked session with party A + party B numbers, then poll or
receive a webhook for status). Once you have Edesy's actual API
reference, adjust the endpoint paths / JSON field names inside this file
— nothing else in the bot needs to change, since every other module only
calls these three functions.
"""
import logging
import requests

import config

log = logging.getLogger("crevio.edesy")

HEADERS = {
    "Authorization": f"Bearer {config.EDESY_API_KEY}",
    "Content-Type": "application/json",
}


class EdesyError(Exception):
    pass


def initiate_masked_call(agent_number: str, customer_number: str) -> dict:
    """
    Starts a masked bridge call: rings agent_number first, then bridges to
    customer_number once agent picks up. Returns Edesy's session/call id.
    """
    url = f"{config.EDESY_BASE_URL}/calls"
    payload = {
        "party_a": agent_number,     # rung first (our bot user)
        "party_b": customer_number,  # bridged in after party_a answers
    }
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=15)
        data = resp.json()
    except Exception as e:
        raise EdesyError(f"Network/parse error calling Edesy: {e}")

    if resp.status_code not in (200, 201):
        raise EdesyError(f"Edesy call init failed: {resp.status_code} {data}")

    return data


def get_call_status(edesy_call_id: str) -> dict:
    """Returns current status + duration_seconds for an ongoing/past call."""
    url = f"{config.EDESY_BASE_URL}/calls/{edesy_call_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        return resp.json()
    except Exception as e:
        raise EdesyError(f"Network/parse error fetching Edesy status: {e}")


def hangup_call(edesy_call_id: str) -> None:
    """Force-ends a call (used when the user's balance runs out mid-call)."""
    url = f"{config.EDESY_BASE_URL}/calls/{edesy_call_id}/hangup"
    try:
        requests.post(url, headers=HEADERS, timeout=10)
    except Exception as e:
        log.warning("Edesy hangup request failed (call may already have ended): %s", e)
