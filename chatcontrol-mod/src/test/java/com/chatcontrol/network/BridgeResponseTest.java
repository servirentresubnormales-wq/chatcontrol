package com.chatcontrol.network;

import com.google.gson.JsonObject;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class BridgeResponseTest {

    @Test
    void testSuccessResponse() {
        BridgeResponse response = BridgeResponse.success("zombie", "Player1", 45);
        assertTrue(response.isSuccess());
        assertEquals("zombie", response.getAction());
        assertEquals("Player1", response.getTarget());
        assertEquals(45, response.getExecutionTimeMs());
        assertEquals(ProtocolConstants.PROTOCOL_VERSION, response.getProtocolVersion());
    }

    @Test
    void testErrorResponse() {
        BridgeResponse response = BridgeResponse.error(ErrorCode.PLAYER_NOT_FOUND, "Player not found: Test");
        assertFalse(response.isSuccess());
        assertEquals(ErrorCode.PLAYER_NOT_FOUND, response.getErrorCode());
        assertEquals("Player not found: Test", response.getMessage());
    }

    @Test
    void testErrorResponseDefaultMessage() {
        BridgeResponse response = BridgeResponse.error(ErrorCode.RATE_LIMITED);
        assertFalse(response.isSuccess());
        assertEquals(ErrorCode.RATE_LIMITED, response.getErrorCode());
        assertEquals(ErrorCode.RATE_LIMITED.getDefaultMessage(), response.getMessage());
    }

    @Test
    void testToJsonSuccess() {
        BridgeResponse response = BridgeResponse.success("zombie", "Player1", 45);
        response.setSource("twitch");
        response.setUser("Viewer123");
        response.setMessageId("msg_001");

        JsonObject json = response.toJson();
        assertTrue(json.get("success").getAsBoolean());
        assertEquals("zombie", json.get("action").getAsString());
        assertEquals("Player1", json.get("target").getAsString());
        assertEquals("twitch", json.get("source").getAsString());
        assertEquals("Viewer123", json.get("user").getAsString());
        assertEquals("msg_001", json.get("message_id").getAsString());
        assertEquals(45, json.get("execution_time_ms").getAsLong());
        assertEquals(1, json.get("protocol_version").getAsInt());
        assertFalse(json.has("error"));
    }

    @Test
    void testToJsonError() {
        BridgeResponse response = BridgeResponse.error(ErrorCode.UNKNOWN_ACTION, "Unknown action: test");

        JsonObject json = response.toJson();
        assertFalse(json.get("success").getAsBoolean());
        assertEquals("UNKNOWN_ACTION", json.get("error").getAsString());
        assertEquals("Unknown action: test", json.get("message").getAsString());
        assertEquals(1, json.get("protocol_version").getAsInt());
        assertFalse(json.has("action"));
    }

    @Test
    void testAllErrorCodes() {
        for (ErrorCode code : ErrorCode.values()) {
            BridgeResponse response = BridgeResponse.error(code);
            assertFalse(response.isSuccess());
            assertEquals(code, response.getErrorCode());
            assertNotNull(response.getMessage());
            assertFalse(response.getMessage().isEmpty());
        }
    }

    @Test
    void testErrorCodesUnique() {
        ErrorCode[] codes = ErrorCode.values();
        java.util.Set<String> codeStrings = new java.util.HashSet<>();
        for (ErrorCode code : codes) {
            assertTrue(codeStrings.add(code.getCode()), "Duplicate error code: " + code.getCode());
        }
    }

    @Test
    void testErrorCodesHaveMessages() {
        for (ErrorCode code : ErrorCode.values()) {
            assertNotNull(code.getDefaultMessage());
            assertFalse(code.getDefaultMessage().isEmpty());
        }
    }

    @Test
    void testProtocolVersionConstant() {
        assertEquals(1, ProtocolConstants.PROTOCOL_VERSION);
        assertEquals("1.0", ProtocolConstants.PROTOCOL_VERSION_STRING);
    }
}
