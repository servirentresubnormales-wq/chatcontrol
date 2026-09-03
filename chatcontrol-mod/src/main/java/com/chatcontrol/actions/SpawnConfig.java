package com.chatcontrol.actions;

public class SpawnConfig {

    public static final int DEFAULT_MIN_DISTANCE = 2;
    public static final int DEFAULT_MAX_ATTEMPTS = 20;
    public static final int CHUNK_SIZE = 16;

    private final int minDistance;
    private final int maxAttempts;

    public SpawnConfig(int minDistance, int maxAttempts) {
        this.minDistance = Math.max(0, minDistance);
        this.maxAttempts = Math.max(1, maxAttempts);
    }

    public static SpawnConfig defaults() {
        return new SpawnConfig(DEFAULT_MIN_DISTANCE, DEFAULT_MAX_ATTEMPTS);
    }

    public int getMinDistance() { return minDistance; }
    public int getMaxAttempts() { return maxAttempts; }

    @Override
    public String toString() {
        return "SpawnConfig{minDistance=" + minDistance + ", maxAttempts=" + maxAttempts + "}";
    }
}
