import json
import pytest
from core.models import BridgeRequest, BridgeResponse, PROTOCOL_VERSION
from core.protocol import serialize_request, deserialize_response, validate_request


class TestBridgeRequest:
    def test_basic_request(self):
        req = BridgeRequest(action="zombie", target="Player1")
        assert req.action == "zombie"
        assert req.target == "Player1"
        assert req.protocol_version == PROTOCOL_VERSION
        assert req.message_id is not None
        assert len(req.message_id) == 32

    def test_to_dict(self):
        req = BridgeRequest(action="zombie", target="Player1", source="twitch", user="Viewer")
        d = req.to_dict()
        assert d["action"] == "zombie"
        assert d["target"] == "Player1"
        assert d["source"] == "twitch"
        assert d["user"] == "Viewer"
        assert d["protocol_version"] == PROTOCOL_VERSION

    def test_to_dict_optional_fields_omitted(self):
        req = BridgeRequest(action="test")
        d = req.to_dict()
        assert "target" not in d
        assert "source" not in d
        assert "user" not in d
        assert "params" not in d
        assert "auth_token" not in d
        assert "metadata" not in d

    def test_from_dict_basic(self):
        data = {"action": "zombie", "target": "Player1", "protocol_version": 1}
        req = BridgeRequest.from_dict(data)
        assert req.action == "zombie"
        assert req.target == "Player1"

    def test_from_dict_player_alias(self):
        data = {"action": "zombie", "player": "Player1", "protocol_version": 1}
        req = BridgeRequest.from_dict(data)
        assert req.target == "Player1"

    def test_from_dict_with_params(self):
        data = {
            "action": "zombie",
            "target": "Player1",
            "params": {"radius": 5},
            "protocol_version": 1,
        }
        req = BridgeRequest.from_dict(data)
        assert req.params == {"radius": 5}

    def test_round_trip(self):
        original = BridgeRequest(
            action="zombie",
            target="Player1",
            source="twitch",
            user="Viewer",
            params={"radius": 4},
        )
        d = original.to_dict()
        restored = BridgeRequest.from_dict(d)
        assert restored.action == original.action
        assert restored.target == original.target
        assert restored.source == original.source
        assert restored.user == original.user
        assert restored.params == original.params

    def test_message_id_unique(self):
        r1 = BridgeRequest(action="test")
        r2 = BridgeRequest(action="test")
        assert r1.message_id != r2.message_id

    def test_custom_message_id(self):
        req = BridgeRequest(action="test", message_id="custom_id")
        assert req.message_id == "custom_id"


class TestBridgeResponse:
    def test_success_response(self):
        resp = BridgeResponse(success=True, action="zombie", target="Player1", message="OK")
        assert resp.success is True
        assert resp.action == "zombie"
        assert resp.error is None

    def test_error_response(self):
        resp = BridgeResponse(success=False, error="PLAYER_NOT_FOUND", message="Not found")
        assert resp.success is False
        assert resp.error == "PLAYER_NOT_FOUND"

    def test_to_dict_success(self):
        resp = BridgeResponse(
            success=True, action="zombie", target="Player1",
            message="OK", execution_time_ms=45,
        )
        d = resp.to_dict()
        assert d["success"] is True
        assert d["action"] == "zombie"
        assert d["execution_time_ms"] == 45
        assert "error" not in d

    def test_to_dict_error(self):
        resp = BridgeResponse(success=False, error="TIMEOUT", message="Timed out")
        d = resp.to_dict()
        assert d["success"] is False
        assert d["error"] == "TIMEOUT"
        assert "action" not in d

    def test_from_dict(self):
        data = {
            "success": True,
            "action": "zombie",
            "message": "OK",
            "protocol_version": 1,
        }
        resp = BridgeResponse.from_dict(data)
        assert resp.success is True
        assert resp.action == "zombie"

    def test_round_trip(self):
        original = BridgeResponse(
            success=True, action="zombie", target="Player1",
            source="twitch", user="Viewer", message="OK",
            execution_time_ms=42, message_id="msg_001",
        )
        d = original.to_dict()
        restored = BridgeResponse.from_dict(d)
        assert restored.success == original.success
        assert restored.action == original.action
        assert restored.source == original.source
        assert restored.execution_time_ms == original.execution_time_ms


class TestProtocol:
    def test_serialize_request(self):
        req = BridgeRequest(action="zombie", target="Player1")
        raw = serialize_request(req)
        data = json.loads(raw)
        assert data["action"] == "zombie"
        assert data["target"] == "Player1"

    def test_deserialize_response(self):
        data = {"success": True, "action": "zombie", "message": "OK", "protocol_version": 1}
        resp = deserialize_response(json.dumps(data))
        assert resp.success is True
        assert resp.action == "zombie"

    def test_deserialize_invalid_json(self):
        from core.exceptions import ProtocolError
        with pytest.raises(ProtocolError):
            deserialize_response("not json")

    def test_deserialize_non_object(self):
        from core.exceptions import ProtocolError
        with pytest.raises(ProtocolError):
            deserialize_response('"just a string"')

    def test_validate_request_ok(self):
        req = BridgeRequest(action="zombie")
        errors = validate_request(req)
        assert errors == []

    def test_validate_request_missing_action(self):
        req = BridgeRequest(action="")
        errors = validate_request(req)
        assert len(errors) == 1
        assert "action" in errors[0]

    def test_validate_request_bad_version(self):
        req = BridgeRequest(action="zombie", protocol_version=999)
        errors = validate_request(req)
        assert len(errors) == 1
        assert "protocol_version" in errors[0]

    def test_response_from_dict_minimal(self):
        data = {"success": False, "message": "error"}
        resp = BridgeResponse.from_dict(data)
        assert resp.success is False
        assert resp.message == "error"
        assert resp.error is None
        assert resp.action is None
