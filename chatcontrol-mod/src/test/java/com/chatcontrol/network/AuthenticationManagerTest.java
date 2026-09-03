package com.chatcontrol.network;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class AuthenticationManagerTest {

    private AuthenticationManager manager;

    @BeforeEach
    void setUp() {
        manager = new AuthenticationManager(true, "test-secret-token", 10, 5, 300);
    }

    @Test
    void testEnabled() {
        assertTrue(manager.isEnabled());
    }

    @Test
    void testDisabled() {
        AuthenticationManager disabled = new AuthenticationManager(false, "", 10, 5, 300);
        assertFalse(disabled.isEnabled());
    }

    @Test
    void testValidateTokenCorrect() {
        assertTrue(manager.validateToken("test-secret-token"));
    }

    @Test
    void testValidateTokenIncorrect() {
        assertFalse(manager.validateToken("wrong-token"));
    }

    @Test
    void testValidateTokenNull() {
        assertFalse(manager.validateToken(null));
    }

    @Test
    void testValidateTokenEmpty() {
        assertFalse(manager.validateToken(""));
    }

    @Test
    void testValidateTokenWhenDisabled() {
        AuthenticationManager disabled = new AuthenticationManager(false, "secret", 10, 5, 300);
        assertTrue(disabled.validateToken("anything"));
        assertTrue(disabled.validateToken(null));
        assertTrue(disabled.validateToken(""));
    }

    @Test
    void testValidateTokenWhenNoTokenConfigured() {
        AuthenticationManager noToken = new AuthenticationManager(true, "", 10, 5, 300);
        assertTrue(noToken.validateToken("anything"));
        assertTrue(noToken.validateToken(null));
    }

    @Test
    void testConnectionStateTransitions() {
        String connId = "conn-1";
        assertEquals(AuthenticationManager.ConnectionAuthState.IDLE, manager.getState(connId));

        manager.setState(connId, AuthenticationManager.ConnectionAuthState.AUTHENTICATING);
        assertEquals(AuthenticationManager.ConnectionAuthState.AUTHENTICATING, manager.getState(connId));

        manager.setState(connId, AuthenticationManager.ConnectionAuthState.AUTHENTICATED);
        assertEquals(AuthenticationManager.ConnectionAuthState.AUTHENTICATED, manager.getState(connId));
    }

    @Test
    void testRemoveConnection() {
        String connId = "conn-2";
        manager.setState(connId, AuthenticationManager.ConnectionAuthState.AUTHENTICATED);
        assertEquals(AuthenticationManager.ConnectionAuthState.AUTHENTICATED, manager.getState(connId));

        manager.removeConnection(connId);
        assertEquals(AuthenticationManager.ConnectionAuthState.IDLE, manager.getState(connId));
    }

    @Test
    void testRateLimitingNotExceeded() {
        String connId = "conn-3";
        assertFalse(manager.isRateLimited(connId));
    }

    @Test
    void testRateLimitingExceeded() {
        String connId = "conn-4";
        for (int i = 0; i < 5; i++) {
            manager.recordFailedAttempt(connId);
        }
        assertTrue(manager.isRateLimited(connId));
    }

    @Test
    void testRateLimitingBelowThreshold() {
        String connId = "conn-5";
        for (int i = 0; i < 4; i++) {
            manager.recordFailedAttempt(connId);
        }
        assertFalse(manager.isRateLimited(connId));
    }

    @Test
    void testClearFailedAttempts() {
        String connId = "conn-6";
        for (int i = 0; i < 5; i++) {
            manager.recordFailedAttempt(connId);
        }
        assertTrue(manager.isRateLimited(connId));

        manager.clearFailedAttempts(connId);
        assertFalse(manager.isRateLimited(connId));
    }

    @Test
    void testRateLimitingDisabled() {
        AuthenticationManager noLimit = new AuthenticationManager(true, "token", 10, 0, 300);
        String connId = "conn-7";
        for (int i = 0; i < 100; i++) {
            noLimit.recordFailedAttempt(connId);
        }
        assertFalse(noLimit.isRateLimited(connId));
    }

    @Test
    void testTimeoutSeconds() {
        assertEquals(10, manager.getTimeoutSeconds());
    }

    @Test
    void testConstantTimeComparison() {
        assertTrue(manager.validateToken("test-secret-token"));
        assertFalse(manager.validateToken("test-secret-tokes"));
        assertFalse(manager.validateToken("test-secret-token "));
        assertFalse(manager.validateToken("test-secret-tokens"));
    }
}
