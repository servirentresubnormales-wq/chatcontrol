package com.chatcontrol.actions;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Random;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

class ChunkPositionHelperTest {

    private ChunkPositionHelper helper;

    @BeforeEach
    void setUp() {
        helper = new ChunkPositionHelper(new Random(42));
    }

    @Test
    void testChunkStartBlockX() {
        assertEquals(0, helper.getChunkStartBlockX(0));
        assertEquals(16, helper.getChunkStartBlockX(1));
        assertEquals(-16, helper.getChunkStartBlockX(-1));
        assertEquals(32, helper.getChunkStartBlockX(2));
    }

    @Test
    void testChunkStartBlockZ() {
        assertEquals(0, helper.getChunkStartBlockZ(0));
        assertEquals(16, helper.getChunkStartBlockZ(1));
        assertEquals(-16, helper.getChunkStartBlockZ(-1));
    }

    @Test
    void testChunkEndBlockX() {
        assertEquals(15, helper.getChunkEndBlockX(0));
        assertEquals(31, helper.getChunkEndBlockX(1));
        assertEquals(-1, helper.getChunkEndBlockX(-1));
    }

    @Test
    void testChunkEndBlockZ() {
        assertEquals(15, helper.getChunkEndBlockZ(0));
        assertEquals(31, helper.getChunkEndBlockZ(1));
        assertEquals(-1, helper.getChunkEndBlockZ(-1));
    }

    @Test
    void testChunkXFromBlock() {
        assertEquals(0, helper.getChunkXFromBlock(0));
        assertEquals(0, helper.getChunkXFromBlock(15));
        assertEquals(1, helper.getChunkXFromBlock(16));
        assertEquals(1, helper.getChunkXFromBlock(31));
        assertEquals(-1, helper.getChunkXFromBlock(-1));
        assertEquals(-1, helper.getChunkXFromBlock(-16));
    }

    @Test
    void testChunkZFromBlock() {
        assertEquals(0, helper.getChunkZFromBlock(0));
        assertEquals(0, helper.getChunkZFromBlock(15));
        assertEquals(1, helper.getChunkZFromBlock(16));
    }

    @Test
    void testRandomXInChunkStaysInside() {
        int chunkX = 5;
        for (int i = 0; i < 100; i++) {
            int x = helper.randomXInChunk(chunkX);
            assertTrue(x >= 80 && x <= 95,
                    "X=" + x + " is outside chunk 5 (80-95)");
        }
    }

    @Test
    void testRandomZInChunkStaysInside() {
        int chunkZ = 3;
        for (int i = 0; i < 100; i++) {
            int z = helper.randomZInChunk(chunkZ);
            assertTrue(z >= 48 && z <= 63,
                    "Z=" + z + " is outside chunk 3 (48-63)");
        }
    }

    @Test
    void testRandomXInChunkNegativeChunk() {
        int chunkX = -2;
        for (int i = 0; i < 100; i++) {
            int x = helper.randomXInChunk(chunkX);
            assertTrue(x >= -32 && x <= -17,
                    "X=" + x + " is outside chunk -2 (-32 to -17)");
        }
    }

    @Test
    void testIsInsideChunkTrue() {
        assertTrue(helper.isInsideChunk(5, 5, 0, 0));
        assertTrue(helper.isInsideChunk(16, 16, 1, 1));
        assertTrue(helper.isInsideChunk(0, 0, 0, 0));
        assertTrue(helper.isInsideChunk(15, 15, 0, 0));
    }

    @Test
    void testIsInsideChunkFalse() {
        assertFalse(helper.isInsideChunk(16, 0, 0, 0));
        assertFalse(helper.isInsideChunk(0, 16, 0, 0));
        assertFalse(helper.isInsideChunk(-1, 0, 0, 0));
        assertFalse(helper.isInsideChunk(0, -1, 0, 0));
    }

    @Test
    void testIsInsideChunkCrossChunkBoundary() {
        assertFalse(helper.isInsideChunk(16, 5, 0, 0));
        assertFalse(helper.isInsideChunk(5, 16, 0, 0));
    }

    @Test
    void testHorizontalDistance() {
        assertEquals(0, helper.horizontalDistance(0, 0, 0, 0), 0.001);
        assertEquals(1, helper.horizontalDistance(0, 0, 1, 0), 0.001);
        assertEquals(1, helper.horizontalDistance(0, 0, 0, 1), 0.001);
        assertEquals(Math.sqrt(2), helper.horizontalDistance(0, 0, 1, 1), 0.001);
        assertEquals(5, helper.horizontalDistance(0, 0, 3, 4), 0.001);
    }

    @Test
    void testMeetsMinDistance() {
        assertTrue(helper.meetsMinDistance(0, 0, 5, 0, 2));
        assertTrue(helper.meetsMinDistance(0, 0, 0, 5, 2));
        assertFalse(helper.meetsMinDistance(0, 0, 1, 0, 2));
        assertFalse(helper.meetsMinDistance(0, 0, 0, 1, 2));
        assertTrue(helper.meetsMinDistance(0, 0, 2, 0, 2));
    }

    @Test
    void testMeetsMinDistanceZeroAlwaysTrue() {
        assertTrue(helper.meetsMinDistance(0, 0, 0, 0, 0));
    }

    @Test
    void testIsValidY() {
        assertTrue(helper.isValidY(0));
        assertTrue(helper.isValidY(-64));
        assertTrue(helper.isValidY(320));
        assertTrue(helper.isValidY(100));
        assertFalse(helper.isValidY(-65));
        assertFalse(helper.isValidY(321));
    }

    @Test
    void testClampY() {
        assertEquals(0, helper.clampY(0));
        assertEquals(-64, helper.clampY(-100));
        assertEquals(320, helper.clampY(400));
        assertEquals(-64, helper.clampY(-64));
        assertEquals(320, helper.clampY(320));
    }

    @Test
    void testFindRandomPositionInChunkAlwaysInsideChunk() {
        int chunkX = 3;
        int chunkZ = 7;
        SpawnConfig config = SpawnConfig.defaults();

        for (int i = 0; i < 100; i++) {
            int encoded = helper.findRandomPositionInChunk(chunkX, chunkZ, 50, 100, config);
            int x = ChunkPositionHelper.decodeX(encoded);
            int z = ChunkPositionHelper.decodeZ(encoded);

            assertTrue(helper.isInsideChunk(x, z, chunkX, chunkZ),
                    "Position (" + x + "," + z + ") is outside chunk (" + chunkX + "," + chunkZ + ")");
        }
    }

    @Test
    void testFindRandomPositionInChunkRespectsMinDistance() {
        int chunkX = 0;
        int chunkZ = 0;
        int streamerX = 8;
        int streamerZ = 8;
        SpawnConfig config = new SpawnConfig(5, 100);

        Set<String> positions = new HashSet<>();
        boolean foundFarPosition = false;

        for (int i = 0; i < 200; i++) {
            int encoded = helper.findRandomPositionInChunk(chunkX, chunkZ, streamerX, streamerZ, config);
            int x = ChunkPositionHelper.decodeX(encoded);
            int z = ChunkPositionHelper.decodeZ(encoded);

            positions.add(x + "," + z);

            if (helper.meetsMinDistance(x, z, streamerX, streamerZ, 5)) {
                foundFarPosition = true;
            }
        }

        assertTrue(foundFarPosition, "Should find at least one position with min distance 5");
        assertTrue(positions.size() > 1, "Should produce varied positions");
    }

    @Test
    void testFindRandomPositionInChunkCornerStreamer() {
        int chunkX = 0;
        int chunkZ = 0;
        int streamerX = 0;
        int streamerZ = 0;
        SpawnConfig config = new SpawnConfig(1, 50);

        for (int i = 0; i < 100; i++) {
            int encoded = helper.findRandomPositionInChunk(chunkX, chunkZ, streamerX, streamerZ, config);
            int x = ChunkPositionHelper.decodeX(encoded);
            int z = ChunkPositionHelper.decodeZ(encoded);

            assertTrue(helper.isInsideChunk(x, z, chunkX, chunkZ),
                    "Position (" + x + "," + z + ") is outside chunk");
        }
    }

    @Test
    void testFindRandomPositionInChunkEdgeStreamer() {
        int chunkX = 0;
        int chunkZ = 0;
        int streamerX = 15;
        int streamerZ = 15;
        SpawnConfig config = new SpawnConfig(2, 50);

        for (int i = 0; i < 100; i++) {
            int encoded = helper.findRandomPositionInChunk(chunkX, chunkZ, streamerX, streamerZ, config);
            int x = ChunkPositionHelper.decodeX(encoded);
            int z = ChunkPositionHelper.decodeZ(encoded);

            assertTrue(helper.isInsideChunk(x, z, chunkX, chunkZ),
                    "Position (" + x + "," + z + ") is outside chunk");
        }
    }

    @Test
    void testFindRandomPositionInChunkNeverExitsChunk() {
        int chunkX = 10;
        int chunkZ = -5;

        for (int minDist = 0; minDist <= 8; minDist++) {
            SpawnConfig config = new SpawnConfig(minDist, 50);
            for (int i = 0; i < 100; i++) {
                int encoded = helper.findRandomPositionInChunk(chunkX, chunkZ, 8, 8, config);
                int x = ChunkPositionHelper.decodeX(encoded);
                int z = ChunkPositionHelper.decodeZ(encoded);

                assertTrue(helper.isInsideChunk(x, z, chunkX, chunkZ),
                        "minDist=" + minDist + ": Position (" + x + "," + z + ") escaped chunk");
            }
        }
    }

    @Test
    void testFindRandomPositionInChunkVaries() {
        SpawnConfig config = SpawnConfig.defaults();
        Set<String> positions = new HashSet<>();

        for (int i = 0; i < 50; i++) {
            int encoded = helper.findRandomPositionInChunk(0, 0, 8, 8, config);
            int x = ChunkPositionHelper.decodeX(encoded);
            int z = ChunkPositionHelper.decodeZ(encoded);
            positions.add(x + "," + z);
        }

        assertTrue(positions.size() > 5, "Should produce varied positions, got " + positions.size());
    }

    @Test
    void testEncodeDecodePosition() {
        int x = 100;
        int z = -200;
        int encoded = ChunkPositionHelper.encodePosition(x, z);
        assertEquals(x, ChunkPositionHelper.decodeX(encoded));
        assertEquals(z, ChunkPositionHelper.decodeZ(encoded));
    }

    @Test
    void testEncodeDecodePositionZero() {
        int encoded = ChunkPositionHelper.encodePosition(0, 0);
        assertEquals(0, ChunkPositionHelper.decodeX(encoded));
        assertEquals(0, ChunkPositionHelper.decodeZ(encoded));
    }

    @Test
    void testEncodeDecodePositionNegative() {
        int encoded = ChunkPositionHelper.encodePosition(-50, -100);
        assertEquals(-50, ChunkPositionHelper.decodeX(encoded));
        assertEquals(-100, ChunkPositionHelper.decodeZ(encoded));
    }

    @Test
    void testEncodeDecodePositionLargeValues() {
        int encoded = ChunkPositionHelper.encodePosition(1000, -1000);
        assertEquals(1000, ChunkPositionHelper.decodeX(encoded));
        assertEquals(-1000, ChunkPositionHelper.decodeZ(encoded));
    }
}
