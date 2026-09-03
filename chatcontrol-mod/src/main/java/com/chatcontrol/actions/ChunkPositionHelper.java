package com.chatcontrol.actions;

import java.util.Random;

public class ChunkPositionHelper {

    public static final int CHUNK_SIZE = 16;
    public static final int MIN_WORLD_Y = -64;
    public static final int MAX_WORLD_Y = 320;

    private final Random random;

    public ChunkPositionHelper(Random random) {
        this.random = random;
    }

    public ChunkPositionHelper() {
        this(new Random());
    }

    public int getChunkStartBlockX(int chunkX) {
        return chunkX * CHUNK_SIZE;
    }

    public int getChunkStartBlockZ(int chunkZ) {
        return chunkZ * CHUNK_SIZE;
    }

    public int getChunkEndBlockX(int chunkX) {
        return chunkX * CHUNK_SIZE + CHUNK_SIZE - 1;
    }

    public int getChunkEndBlockZ(int chunkZ) {
        return chunkZ * CHUNK_SIZE + CHUNK_SIZE - 1;
    }

    public int getChunkXFromBlock(int blockX) {
        return blockX >> 4;
    }

    public int getChunkZFromBlock(int blockZ) {
        return blockZ >> 4;
    }

    public int randomXInChunk(int chunkX) {
        int start = getChunkStartBlockX(chunkX);
        return start + random.nextInt(CHUNK_SIZE);
    }

    public int randomZInChunk(int chunkZ) {
        int start = getChunkStartBlockZ(chunkZ);
        return start + random.nextInt(CHUNK_SIZE);
    }

    public boolean isInsideChunk(int blockX, int blockZ, int chunkX, int chunkZ) {
        int startBlockX = getChunkStartBlockX(chunkX);
        int startBlockZ = getChunkStartBlockZ(chunkZ);
        return blockX >= startBlockX && blockX <= startBlockX + CHUNK_SIZE - 1
            && blockZ >= startBlockZ && blockZ <= startBlockZ + CHUNK_SIZE - 1;
    }

    public double horizontalDistance(int x1, int z1, int x2, int z2) {
        double dx = x1 - x2;
        double dz = z1 - z2;
        return Math.sqrt(dx * dx + dz * dz);
    }

    public boolean meetsMinDistance(int x1, int z1, int x2, int z2, int minDistance) {
        return horizontalDistance(x1, z1, x2, z2) >= minDistance;
    }

    public boolean isValidY(int y) {
        return y >= MIN_WORLD_Y && y <= MAX_WORLD_Y;
    }

    public int clampY(int y) {
        return Math.max(MIN_WORLD_Y, Math.min(MAX_WORLD_Y, y));
    }

    public int findRandomPositionInChunk(
            int chunkX, int chunkZ,
            int streamerX, int streamerZ,
            SpawnConfig config) {

        for (int attempt = 0; attempt < config.getMaxAttempts(); attempt++) {
            int x = randomXInChunk(chunkX);
            int z = randomZInChunk(chunkZ);

            if (meetsMinDistance(x, z, streamerX, streamerZ, config.getMinDistance())) {
                return encodePosition(x, z);
            }
        }

        for (int attempt = 0; attempt < config.getMaxAttempts(); attempt++) {
            int x = randomXInChunk(chunkX);
            int z = randomZInChunk(chunkZ);
            return encodePosition(x, z);
        }

        return encodePosition(
            getChunkStartBlockX(chunkX),
            getChunkStartBlockZ(chunkZ)
        );
    }

    public int findRandomYInChunk(int chunkX, int chunkZ, int preferredY) {
        int y = clampY(preferredY);
        return y;
    }

    public int findSafeTeleportY(int chunkX, int chunkZ, int preferredY) {
        return clampY(preferredY);
    }

    public static int encodePosition(int x, int z) {
        return (x << 16) | (z & 0xFFFF);
    }

    public static int decodeX(int encoded) {
        return encoded >> 16;
    }

    public static int decodeZ(int encoded) {
        return (encoded << 16) >> 16;
    }
}
