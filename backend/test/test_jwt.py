import time

import pytest

from app.core.jwt import (
    TokenExpiredError,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    verify_refresh_token,
    get_jti,
    get_session_id,
    get_subject,
)


def test_create_access_token():

    token = create_access_token("user-123")

    payload = verify_access_token(token)

    assert payload.sub == "user-123"
    assert payload.is_access_token
    assert not payload.is_refresh_token


def test_create_refresh_token():

    token = create_refresh_token("user-123")

    payload = verify_refresh_token(token)

    assert payload.sub == "user-123"
    assert payload.is_refresh_token
    assert not payload.is_access_token


def test_access_rejected_as_refresh():

    token = create_access_token("user-123")

    with pytest.raises(Exception):
        verify_refresh_token(token)


def test_refresh_rejected_as_access():

    token = create_refresh_token("user-123")

    with pytest.raises(Exception):
        verify_access_token(token)


def test_jti_exists():

    token = create_access_token("abc")

    jti = get_jti(token)

    assert isinstance(jti, str)
    assert len(jti) > 20


def test_session_id_exists():

    token = create_access_token("abc")

    sid = get_session_id(token)

    assert isinstance(sid, str)
    assert len(sid) > 20


def test_subject():

    token = create_access_token("my-user")

    assert get_subject(token) == "my-user"


def test_expired_token():

    from datetime import timedelta

    token = create_access_token(
        "user-1",
        expires_delta=timedelta(seconds=1),
    )

    time.sleep(2)

    with pytest.raises(TokenExpiredError):
        verify_access_token(token)


def test_tampered_token():

    token = create_access_token("user")

    token = token[:-1] + "A"

    with pytest.raises(Exception):
        verify_access_token(token)


def test_tokens_are_unique():

    a = create_access_token("1")
    b = create_access_token("1")

    assert a != b


def test_session_ids_differ():

    t1 = create_access_token("1")
    t2 = create_access_token("1")

    assert get_session_id(t1) != get_session_id(t2)


def test_jtis_are_unique():

    t1 = create_access_token("1")
    t2 = create_access_token("1")

    assert get_jti(t1) != get_jti(t2)


def test_invalid_signature():

    token = create_access_token("user")

    pieces = token.split(".")

    pieces[2] = "AAAAAAAAAAAA"

    bad = ".".join(pieces)

    with pytest.raises(Exception):
        verify_access_token(bad)


def test_wrong_audience():

    token = create_access_token(
        "user",
        audience="mobile-app",
    )

    with pytest.raises(Exception):
        verify_access_token(token)
