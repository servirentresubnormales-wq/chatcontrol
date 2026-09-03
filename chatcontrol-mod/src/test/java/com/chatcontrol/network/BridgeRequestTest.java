package com.chatcontrol.network;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class BridgeRequestTest {

    @Test
    void testFromJsonBasic() {
        JsonObject json = new JsonObject();
        json.addProperty("action", "zombie");
        json.addProperty("target", "Player1");
        json.addProperty("protocol_version", 1);

        BridgeRequest request = BridgeRequest.fromJson(json);
        assertEquals("zombie", request.getAction());
        assertEquals("Player1", request.getTarget());
        assertEquals(Integer.valueOf(1), request.getProtocolVersion());
    }

    @Test
    void testFromJsonWithAllFields() {
        JsonObject json = new JsonObject();
        json.addProperty("action", "spiders");
        json.addProperty("target", "Player1");
        json.addProperty("source", "twitch");
        json.addProperty("user", "Viewer123");
        json.addProperty("message_id", "msg_001");
        json.addProperty("protocol_version", 1);
        json.addProperty("auth_token", "token123");

        JsonObject params = new JsonObject();
        params.addProperty("amount", 5);
        json.add("params", params);

        JsonObject metadata = new JsonObject();
        metadata.addProperty("channel", "test_channel");
        json.add("metadata", metadata);

        BridgeRequest request = BridgeRequest.fromJson(json);
        assertEquals("spiders", request.getAction());
        assertEquals("Player1", request.getTarget());
        assertEquals("twitch", request.getSource());
        assertEquals("Viewer123", request.getUser());
        assertEquals("msg_001", request.getMessageId());
        assertEquals(Integer.valueOf(1), request.getProtocolVersion());
        assertEquals("token123", request.getAuthToken());
        assertNotNull(request.getParams());
        assertEquals(5, request.getParams().get("amount").getAsInt());
        assertNotNull(request.getMetadata());
        assertEquals("test_channel", request.getMetadata().get("channel").getAsString());
    }

    @Test
    void testFromJsonPlayerAlias() {
        JsonObject json = new JsonObject();
        json.addProperty("action", "zombie");
        json.addProperty("player", "Player1");
        json.addProperty("protocol_version", 1);

        BridgeRequest request = BridgeRequest.fromJson(json);
        assertEquals("Player1", request.getTarget());
    }

    @Test
    void testFromJsonMinimal() {
        JsonObject json = new JsonObject();
        json.addProperty("action", "chickens");
        json.addProperty("protocol_version", 1);

        BridgeRequest request = BridgeRequest.fromJson(json);
        assertEquals("chickens", request.getAction());
        assertNull(request.getTarget());
        assertNull(request.getSource());
        assertNull(request.getUser());
        assertNull(request.getParams());
    }

    @Test
    void testToJson() {
        BridgeRequest request = new BridgeRequest("zombie", "Player1");
        request.setSource("twitch");
        request.setUser("Viewer123");

        JsonObject json = request.toJson();
        assertEquals("zombie", json.get("action").getAsString());
        assertEquals("Player1", json.get("target").getAsString());
        assertEquals("twitch", json.get("source").getAsString());
        assertEquals("Viewer123", json.get("user").getAsString());
        assertEquals(1, json.get("protocol_version").getAsInt());
    }

    @Test
    void testHasValidProtocolVersion() {
        BridgeRequest valid = new BridgeRequest();
        valid.setProtocolVersion(1);
        assertTrue(valid.hasValidProtocolVersion());

        BridgeRequest invalid = new BridgeRequest();
        invalid.setProtocolVersion(999);
        assertFalse(invalid.hasValidProtocolVersion());

        BridgeRequest null_version = new BridgeRequest();
        assertFalse(null_version.hasValidProtocolVersion());
    }

    @Test
    void testFromJsonNullFields() {
        JsonObject json = new JsonObject();
        json.addProperty("action", "test");

        BridgeRequest request = BridgeRequest.fromJson(json);
        assertEquals("test", request.getAction());
        assertNull(request.getTarget());
        assertNull(request.getSource());
    }
}
