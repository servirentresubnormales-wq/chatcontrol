package com.chatcontrol.network;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.concurrent.atomic.AtomicInteger;

public class AuthenticationManager {

    private final boolean enabled;
    private final String expectedToken;
    private final int timeoutSeconds;
    private final int maxFailedAttempts;
    private final int rateLimitWindowSeconds;

    private final Map<String, ConnectionAuthState> connectionStates = new ConcurrentHashMap<>();
    private final Map<String, Deque<Long>> failedAttempts = new ConcurrentHashMap<>();

    public AuthenticationManager(boolean enabled, String token, int timeoutSeconds,
                                  int maxFailedAttempts, int rateLimitWindowSeconds) {
        this.enabled = enabled;
        this.expectedToken = token != null ? token : "";
        this.timeoutSeconds = timeoutSeconds;
        this.maxFailedAttempts = maxFailedAttempts;
        this.rateLimitWindowSeconds = rateLimitWindowSeconds;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public int getTimeoutSeconds() {
        return timeoutSeconds;
    }

    public ConnectionAuthState getState(String connectionId) {
        return connectionStates.getOrDefault(connectionId, ConnectionAuthState.IDLE);
    }

    public void setState(String connectionId, ConnectionAuthState state) {
        connectionStates.put(connectionId, state);
    }

    public void removeConnection(String connectionId) {
        connectionStates.remove(connectionId);
    }

    public boolean isRateLimited(String connectionId) {
        if (maxFailedAttempts <= 0) return false;

        Deque<Long> attempts = failedAttempts.computeIfAbsent(connectionId, k -> new ConcurrentLinkedDeque<>());
        long cutoff = System.currentTimeMillis() - (rateLimitWindowSeconds * 1000L);

        while (!attempts.isEmpty() && attempts.peekFirst() < cutoff) {
            attempts.pollFirst();
        }

        return attempts.size() >= maxFailedAttempts;
    }

    public void recordFailedAttempt(String connectionId) {
        Deque<Long> attempts = failedAttempts.computeIfAbsent(connectionId, k -> new ConcurrentLinkedDeque<>());
        attempts.addLast(System.currentTimeMillis());
    }

    public void clearFailedAttempts(String connectionId) {
        failedAttempts.remove(connectionId);
    }

    public boolean validateToken(String token) {
        if (!enabled) return true;
        if (expectedToken.isEmpty()) return true;
        if (token == null) return false;
        return constantTimeCompare(expectedToken, token);
    }

    private boolean constantTimeCompare(String expected, String actual) {
        byte[] expectedBytes = expected.getBytes(java.nio.charset.StandardCharsets.UTF_8);
        byte[] actualBytes = actual.getBytes(java.nio.charset.StandardCharsets.UTF_8);

        if (expectedBytes.length != actualBytes.length) {
            MessageDigest.isEqual(expectedBytes, new byte[expectedBytes.length]);
            return false;
        }

        return MessageDigest.isEqual(expectedBytes, actualBytes);
    }

    public enum ConnectionAuthState {
        IDLE,
        AUTHENTICATING,
        AUTHENTICATED,
        REJECTED,
        CLOSED
    }
}
