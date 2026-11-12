"""The WhatsApp webhook under generated requests: forged updates never reach the handlers.

pywa answers a correctly signed update at once and handles it in a background task, which the
test client runs before returning: an exception there fails the test, though Meta got its 200.
"""

import hashlib
import hmac
import json

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from tests.fixtures import WEBHOOK_APP_SECRET, WEBHOOK_VERIFY_TOKEN

# What an HTTP header or query value can carry here: printable ASCII.
_PRINTABLE = st.text(alphabet=st.characters(min_codepoint=33, max_codepoint=126), max_size=100)
_JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False, allow_infinity=False) | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=20,
)
# Meta's envelope, which pywa reads `entry[0].changes[0].field` from, around a value of any shape.
_ENVELOPE = st.fixed_dictionaries(
    {
        "object": st.text(),
        "entry": st.lists(
            st.fixed_dictionaries(
                {
                    "id": st.text(),
                    "changes": st.lists(st.fixed_dictionaries({"field": st.text(), "value": _JSON}), min_size=1),
                }
            ),
            min_size=1,
        ),
    }
)
# The client fixture lives for the whole test rather than one example: it keeps no state between requests.
_FUZZ = settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
# Missing, the header fails FastAPI's validation of pywa's route; empty, pywa's own check; anything else, the HMAC.
_REFUSALS = {None: 422, "": 401}
_FORGED = 403


def _signed(body: bytes) -> dict[str, str]:
    digest = hmac.new(WEBHOOK_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={digest}"}


@_FUZZ
@given(body=st.binary(max_size=2048), signature=st.one_of(st.none(), st.just(""), _PRINTABLE))
def test_an_unsigned_or_forged_update_is_refused(whatsapp_webhook, body, signature):
    client, handlers = whatsapp_webhook
    headers = {} if signature is None else {"X-Hub-Signature-256": signature}

    response = client.post("/", content=body, headers=headers)

    assert response.status_code == _REFUSALS.get(signature, _FORGED)
    assert [handler.await_count for handler in handlers] == [0, 0]


def _is_json(body: bytes) -> bool:
    try:
        json.loads(body)
    except ValueError:
        return False
    return True


@_FUZZ
@given(body=st.binary(max_size=2048))
def test_a_signed_body_that_is_not_json_is_dropped_quietly(whatsapp_webhook, body):
    assume(not _is_json(body))
    client, _ = whatsapp_webhook

    response = client.post("/", content=body, headers=_signed(body))

    assert response.status_code == 200


@_FUZZ
@given(update=_ENVELOPE)
def test_a_signed_update_of_any_shape_is_handled_without_an_exception(whatsapp_webhook, update):
    client, _ = whatsapp_webhook
    body = json.dumps(update).encode()

    response = client.post("/", content=body, headers=_signed(body))

    assert response.status_code == 200


@pytest.mark.xfail(
    strict=True,
    raises=KeyError,
    reason="pywa 4.5.0: an update without entry[0].changes[0].field raises again in the except branch that "
    "logs it (pywa/server.py `_call_handlers`). Only Meta can sign, and Meta always sends the envelope.",
)
def test_a_signed_update_without_the_envelope_is_handled_without_an_exception(whatsapp_webhook):
    client, _ = whatsapp_webhook

    client.post("/", content=b"{}", headers=_signed(b"{}"))


@_FUZZ
@given(token=_PRINTABLE, challenge=_PRINTABLE)
def test_the_handshake_refuses_any_other_token(whatsapp_webhook, token, challenge):
    assume(token != WEBHOOK_VERIFY_TOKEN)
    client, _ = whatsapp_webhook

    response = client.get("/", params={"hub.mode": "subscribe", "hub.verify_token": token, "hub.challenge": challenge})

    assert response.status_code == 403


@_FUZZ
@given(challenge=_PRINTABLE)
def test_the_handshake_echoes_the_challenge_for_the_verify_token(whatsapp_webhook, challenge):
    client, _ = whatsapp_webhook
    params = {"hub.mode": "subscribe", "hub.verify_token": WEBHOOK_VERIFY_TOKEN, "hub.challenge": challenge}

    response = client.get("/", params=params)

    assert (response.status_code, response.text) == (200, challenge)
