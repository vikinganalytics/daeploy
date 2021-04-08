import sys
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.responses import JSONResponse

from manager.constants import DAEPLOY_REQUIRED_PASSWORD_LENGTH
import manager.license as lic


@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="AsyncMock not introduced until 3.8"
)
@pytest.mark.asyncio
async def test_door_man():
    from unittest.mock import AsyncMock

    request = "mumbojumbo"

    # Set expiration time to now +1 second
    old_exp = lic.EXPIRATION_TIME
    lic.EXPIRATION_TIME = datetime.now(tz=timezone.utc) + timedelta(seconds=1)

    try:

        # Check that we are allowed in at the beginning
        call_next = AsyncMock()
        await lic.validity_door_man(request, call_next)
        call_next.assert_awaited_once_with(request)

        # Sleep for a second
        await asyncio.sleep(1)

        # Try again, this time we should not be allowed in
        call_next = AsyncMock()
        res = await lic.validity_door_man(request, call_next)
        call_next.assert_not_awaited()
        assert isinstance(res, JSONResponse)
        assert res.status_code == 403

    finally:
        lic.EXPIRATION_TIME = old_exp


def test_with_mumbojumbo_token(caplog, pinned):
    caplog.set_level("INFO")

    token = "skjdnblaknsk"

    exp_before = lic.EXPIRATION_TIME

    lic.activate(token)

    assert exp_before == lic.EXPIRATION_TIME
    assert pinned == caplog.text


def test_with_dev_token(caplog, pinned):
    caplog.set_level("INFO")

    # Set expiry date: 2030-01-01, NO usernames embedded
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE2MDc5NDM3NjUsImV4cCI6MTg5MzQ1NjAwMCwidXNlcm5hbWVzIjpbXX0.lsk1esgP08EWYkNXY_m9igaWej5Jk13wuxyUrWaVvOoPQQc9B4E0tQCwGXn9US_3bOkCED_YboJwLqV4ap8h7FsbDmPkSfop7J-SmZOwg4etjE_6doa7MEq_PXIwUdwIgJ_VHFshVtJ_rZWT-1qk1Oh9OEeXiEnrIukahK8kAP4"

    lic.activate(token)

    assert (
        lic.EXPIRATION_TIME.timestamp()
        == datetime(2030, 1, 1, tzinfo=timezone.utc).timestamp()
    )
    assert pinned == caplog.text


@patch.object(lic, "add_user_record")
def test_with_user_token(mock):

    # Set expiry date: 2030-01-01, "urban" and "rune" embedded users
    token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE2MDc5NDM4MTcsImV4cCI6MTg5MzQ1NjAwMCwidXNlcm5hbWVzIjpbInVyYmFuIiwicnVuZSJdfQ.GEHX8G9t4sklM_EFfIisbt4wZOZ2G8EkuhSsHEDt4KpCM6KJd3D1OIQe1vnxfyBU21vh1gE7ykTHrMwYbdUBp6vVww9waBYhlYqXnfG7mkBiX3oDb_u8YJiHpxIPKheoJmBGgfgK-1RFfoD4XDa5ZvqkaJSQMgvNtPwKn-cbQKo"

    lic.activate(token)

    assert mock.call_count == 2
    assert (
        lic.EXPIRATION_TIME.timestamp()
        == datetime(2030, 1, 1, tzinfo=timezone.utc).timestamp()
    )
    for expected, given in zip(["urban", "rune"], mock.call_args_list):
        assert expected == given[0][0]
        assert isinstance(given[0][1], str)
        assert len(given[0][1]) == DAEPLOY_REQUIRED_PASSWORD_LENGTH
