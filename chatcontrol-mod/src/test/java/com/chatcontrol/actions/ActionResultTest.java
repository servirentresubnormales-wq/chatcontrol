package com.chatcontrol.actions;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ActionResultTest {

    @Test
    void testSuccess() {
        ActionResult result = ActionResult.success("OK");
        assertTrue(result.isSuccess());
        assertEquals("OK", result.getMessage());
    }

    @Test
    void testFailure() {
        ActionResult result = ActionResult.failure("Error");
        assertFalse(result.isSuccess());
        assertEquals("Error", result.getMessage());
    }

    @Test
    void testToStringSuccess() {
        ActionResult result = ActionResult.success("done");
        assertEquals("[OK] done", result.toString());
    }

    @Test
    void testToStringFailure() {
        ActionResult result = ActionResult.failure("fail");
        assertEquals("[FAIL] fail", result.toString());
    }
}
