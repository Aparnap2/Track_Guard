"""Unit tests for ERPNextClient — pure-stdlib Frappe REST client."""
import json
import os
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

import pytest
from src.integrations.erpnext_client import ERPNextClient, ERPNextError


class TestERPNextClientInit:
    @patch.dict(os.environ, {
        "ERPNEXT_URL": "https://erp.example.com",
        "ERPNEXT_API_KEY": "test-key",
        "ERPNEXT_API_SECRET": "test-secret",
    }, clear=True)
    def test_init_reads_env_vars(self):
        client = ERPNextClient()
        assert client.base == "https://erp.example.com"
        assert client._auth == "token test-key:test-secret"

    @patch.dict(os.environ, {}, clear=True)
    def test_init_defaults_when_no_env(self):
        client = ERPNextClient()
        assert client.base == "http://localhost:8080"
        assert client._auth == "token :"


class TestERPNextClientRequest:
    @patch("src.integrations.erpnext_client.urllib.request.urlopen")
    def test_request_returns_parsed_json(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": {"name": "ISS-001"}}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        client = ERPNextClient()
        result = client._request("GET", "/api/test")
        assert result == {"data": {"name": "ISS-001"}}

    @patch("src.integrations.erpnext_client.urllib.request.urlopen")
    def test_request_handles_http_error_with_server_messages(self, mock_urlopen):
        error_body = json.dumps({
            "_server_messages": json.dumps([
                json.dumps({"message": "DocType Issue not set"})
            ])
        }).encode()
        mock_urlopen.side_effect = HTTPError(
            url="/api/test", code=400, msg="Bad Request",
            hdrs={}, fp=type("FakeFile", (), {"read": lambda s: error_body})(),
        )
        client = ERPNextClient()
        with pytest.raises(ERPNextError) as exc:
            client._request("GET", "/api/test")
        assert "DocType Issue not set" in str(exc.value)


class TestERPNextClientPublicAPI:
    @patch.object(ERPNextClient, "_request")
    def test_get_returns_data(self, mock_request):
        mock_request.return_value = {"data": {"name": "ISS-001", "status": "Open"}}
        client = ERPNextClient()
        result = client.get("Issue", "ISS-001")
        assert result == {"name": "ISS-001", "status": "Open"}

    @patch.object(ERPNextClient, "_request")
    def test_list_returns_message(self, mock_request):
        mock_request.return_value = {"message": [{"name": "ISS-001"}]}
        client = ERPNextClient()
        result = client.list("Issue")
        assert result == [{"name": "ISS-001"}]

    @patch.object(ERPNextClient, "_request")
    def test_count_returns_int(self, mock_request):
        mock_request.return_value = {"message": 42}
        client = ERPNextClient()
        result = client.count("Issue")
        assert result == 42
        assert isinstance(result, int)

    @patch.object(ERPNextClient, "_request")
    def test_get_value_returns_field(self, mock_request):
        mock_request.return_value = {"message": {"status": "Open"}}
        client = ERPNextClient()
        result = client.get_value("Issue", [["name", "=", "ISS-001"]], "status")
        assert result == "Open"
