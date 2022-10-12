import datetime as dt
from unittest import mock

from fastapi import status

from fmn.api import main


@mock.patch("fmn.api.main.get_settings")
@mock.patch("fmn.api.main.app")
def test_add_middlewares(app, get_settings):
    get_settings.return_value = mock.Mock(cors_origins="https://foo")
    main.add_middlewares()

    calls = [
        mock.call(
            main.CORSMiddleware,
            allow_origins=["https://foo"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]
    app.add_middleware.assert_has_calls(calls)
    assert app.add_middleware.call_count == 2


async def test_read_root():
    request = mock.Mock()
    creds = mock.Mock(scheme="bearer", credentials="abcd-1234")
    identity = mock.Mock(expires_at=dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc))
    identity.name = "foo"  # name can't be set in the constructor of Mock()

    result = await main.read_root(request=request, creds=creds, identity=identity)

    assert result["Hello"] == "World"
    assert result["creds"].scheme == "bearer"
    assert result["creds"].credentials == "abcd-1234"
    assert result["identity"].name == "foo"
    assert isinstance(result["identity"].expires_at, dt.datetime)


def test_get_settings():
    assert isinstance(main.get_settings(), main.Settings)


def test_get_fasjson_client(mocker):
    settings = main.Settings(services={"fasjson_url": "http://fasjson.test/"})
    mocker.patch.object(main.FasjsonClient, "_make_bravado_client")
    client = main.get_fasjson_client(settings)
    assert client._base_url == settings.services.fasjson_url


def test_get_user_info(fasjson_user, fasjson_user_data, client):
    """Test that get_user_info() dispatches to FASJSON."""
    username = fasjson_user_data["username"]
    response = client.get(f"/user/{username}/info")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == fasjson_user_data
