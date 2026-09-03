package com.chatcontrol.state;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SystemStateTest {

    @Test
    void testInitialState() {
        SystemState state = new SystemState();
        assertFalse(state.isEnabled());
        assertEquals(0, state.getTotalActionsExecuted());
        assertEquals(0, state.getUptimeMs());
        assertNull(state.getLastActionUser());
    }

    @Test
    void testEnableDisable() {
        SystemState state = new SystemState();
        state.setEnabled(true);
        assertTrue(state.isEnabled());
        state.setEnabled(false);
        assertFalse(state.isEnabled());
    }

    @Test
    void testIncrementActionsExecuted() {
        SystemState state = new SystemState();
        state.incrementActionsExecuted();
        state.incrementActionsExecuted();
        state.incrementActionsExecuted();
        assertEquals(3, state.getTotalActionsExecuted());
    }

    @Test
    void testReset() {
        SystemState state = new SystemState();
        state.setEnabled(true);
        state.incrementActionsExecuted();
        state.incrementActionsExecuted();
        state.reset();
        assertFalse(state.isEnabled());
        assertEquals(0, state.getTotalActionsExecuted());
        assertEquals(0, state.getUptimeMs());
        assertNull(state.getLastActionUser());
    }

    @Test
    void testUptimeWhenDisabled() {
        SystemState state = new SystemState();
        assertEquals(0, state.getUptimeMs());
    }

    @Test
    void testLastActionUser() {
        SystemState state = new SystemState();
        java.util.UUID uuid = java.util.UUID.randomUUID();
        state.setLastActionUser(uuid);
        assertEquals(uuid, state.getLastActionUser());
    }
}
