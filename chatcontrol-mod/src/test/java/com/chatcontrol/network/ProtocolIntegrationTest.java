package com.chatcontrol.network;

import com.chatcontrol.actions.ActionParameters;
import com.chatcontrol.actions.ActionResult;
import com.google.gson.JsonObject;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ProtocolIntegrationTest {

    @Test
    void testRequestResponseRoundTrip() {
        JsonObject requestJson = new JsonObject();
        requestJson.addProperty("action", "zombie");
        requestJson.addProperty("target", "Player1");
        requestJson.addProperty("source", "twitch");
        requestJson.addProperty("user", "Viewer123");
        requestJson.addProperty("protocol_version", 1);
        requestJson.addProperty("message_id", "msg_001");

        BridgeRequest request = BridgeRequest.fromJson(requestJson);
        assertEquals("zombie", request.getAction());
        assertEquals("Player1", request.getTarget());
        assertEquals("twitch", request.getSource());

        BridgeResponse response = BridgeResponse.success("zombie", request.getTarget(), 50);
        response.setSource(request.getSource());
        response.setUser(request.getUser());
        response.setMessageId(request.getMessageId());

        JsonObject responseJson = response.toJson();
        assertTrue(responseJson.get("success").getAsBoolean());
        assertEquals("zombie", responseJson.get("action").getAsString());
        assertEquals("twitch", responseJson.get("source").getAsString());
        assertEquals("Viewer123", responseJson.get("user").getAsString());
        assertEquals("msg_001", responseJson.get("message_id").getAsString());
    }

    @Test
    void testErrorRoundTrip() {
        BridgeResponse response = BridgeResponse.error(ErrorCode.PLAYER_NOT_FOUND, "Player not found: Test");
        JsonObject json = response.toJson();

        assertFalse(json.get("success").getAsBoolean());
        assertEquals("PLAYER_NOT_FOUND", json.get("error").getAsString());
        assertEquals("Player not found: Test", json.get("message").getAsString());
    }

    @Test
    void testActionResultToBridgeResponse() {
        ActionResult actionResult = ActionResult.success("Executed");
        assertEquals(ErrorCode.class, actionResult.getErrorCode() == null ? ErrorCode.class : actionResult.getErrorCode().getClass());
        assertTrue(actionResult.isSuccess());

        ActionResult failureResult = ActionResult.failure(ErrorCode.ON_COOLDOWN, "Wait 5s");
        assertFalse(failureResult.isSuccess());
        assertEquals(ErrorCode.ON_COOLDOWN, failureResult.getErrorCode());
        assertEquals("Wait 5s", failureResult.getMessage());
    }

    @Test
    void testRequestBackwardCompatibility() {
        JsonObject oldFormat = new JsonObject();
        oldFormat.addProperty("action", "zombie");
        oldFormat.addProperty("player", "Player1");

        BridgeRequest request = BridgeRequest.fromJson(oldFormat);
        assertEquals("zombie", request.getAction());
        assertEquals("Player1", request.getTarget());
    }

    @Test
    void testRequestWithNullParams() {
        JsonObject json = new JsonObject();
        json.addProperty("action", "zombie");
        json.addProperty("protocol_version", 1);

        BridgeRequest request = BridgeRequest.fromJson(json);
        assertNull(request.getParams());

        ActionParameters params = new ActionParameters();
        assertNotNull(params);
        assertFalse(params.has("anything"));
    }

    @Test
    void testResponseWithMetadata() {
        BridgeResponse response = BridgeResponse.success("zombie", "Player1", 50);
        JsonObject metadata = new JsonObject();
        metadata.addProperty("extra", "data");
        response.setMetadata(metadata);

        JsonObject json = response.toJson();
        assertNotNull(json.get("metadata"));
        assertEquals("data", json.get("metadata").getAsJsonObject().get("extra").getAsString());
    }
}
