package com.chatcontrol.actions;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ActionParametersTest {

    @Test
    void testSetAndGet() {
        ActionParameters params = new ActionParameters();
        params.set("key", "value");
        assertEquals("value", params.get("key"));
    }

    @Test
    void testGetWithDefault() {
        ActionParameters params = new ActionParameters();
        assertEquals("default", params.get("missing", "default"));
        params.set("key", "value");
        assertEquals("value", params.get("key", "default"));
    }

    @Test
    void testGetInt() {
        ActionParameters params = new ActionParameters();
        assertEquals(42, params.getInt("missing", 42));
        params.set("num", "100");
        assertEquals(100, params.getInt("num", 0));
    }

    @Test
    void testGetIntInvalid() {
        ActionParameters params = new ActionParameters();
        params.set("bad", "abc");
        assertEquals(99, params.getInt("bad", 99));
    }

    @Test
    void testGetFloat() {
        ActionParameters params = new ActionParameters();
        assertEquals(3.14f, params.getFloat("missing", 3.14f), 0.001f);
        params.set("pi", "3.14");
        assertEquals(3.14f, params.getFloat("pi", 0), 0.001f);
    }

    @Test
    void testGetFloatInvalid() {
        ActionParameters params = new ActionParameters();
        params.set("bad", "not_a_float");
        assertEquals(1.5f, params.getFloat("bad", 1.5f), 0.001f);
    }

    @Test
    void testGetBoolean() {
        ActionParameters params = new ActionParameters();
        assertFalse(params.getBoolean("missing", false));
        params.set("flag", "true");
        assertTrue(params.getBoolean("flag", false));
        params.set("flag2", "false");
        assertFalse(params.getBoolean("flag2", true));
    }

    @Test
    void testHas() {
        ActionParameters params = new ActionParameters();
        assertFalse(params.has("key"));
        params.set("key", "value");
        assertTrue(params.has("key"));
    }

    @Test
    void testGetAll() {
        ActionParameters params = new ActionParameters();
        params.set("a", "1");
        params.set("b", "2");
        var all = params.getAll();
        assertEquals(2, all.size());
        assertEquals("1", all.get("a"));
        assertEquals("2", all.get("b"));
    }

    @Test
    void testFromMap() {
        var map = java.util.Map.of("x", "10", "y", "20");
        ActionParameters params = ActionParameters.fromMap(map);
        assertEquals("10", params.get("x"));
        assertEquals("20", params.get("y"));
    }

    @Test
    void testFromNullMap() {
        ActionParameters params = ActionParameters.fromMap(null);
        assertNotNull(params);
        assertFalse(params.has("anything"));
    }

    @Test
    void testNullValue() {
        ActionParameters params = new ActionParameters();
        assertNull(params.get("missing"));
        assertEquals("default", params.get("missing", "default"));
    }
}
