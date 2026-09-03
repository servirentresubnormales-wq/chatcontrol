package com.chatcontrol.actions;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SpawnConfigTest {

    @Test
    void testDefaults() {
        SpawnConfig config = SpawnConfig.defaults();
        assertEquals(2, config.getMinDistance());
        assertEquals(20, config.getMaxAttempts());
    }

    @Test
    void testCustomValues() {
        SpawnConfig config = new SpawnConfig(5, 30);
        assertEquals(5, config.getMinDistance());
        assertEquals(30, config.getMaxAttempts());
    }

    @Test
    void testNegativeMinDistanceClampedToZero() {
        SpawnConfig config = new SpawnConfig(-5, 10);
        assertEquals(0, config.getMinDistance());
    }

    @Test
    void testZeroMaxAttemptsClampedToOne() {
        SpawnConfig config = new SpawnConfig(2, 0);
        assertEquals(1, config.getMaxAttempts());
    }

    @Test
    void testNegativeMaxAttemptsClampedToOne() {
        SpawnConfig config = new SpawnConfig(2, -10);
        assertEquals(1, config.getMaxAttempts());
    }

    @Test
    void testToString() {
        SpawnConfig config = new SpawnConfig(3, 15);
        String str = config.toString();
        assertTrue(str.contains("3"));
        assertTrue(str.contains("15"));
    }
}
