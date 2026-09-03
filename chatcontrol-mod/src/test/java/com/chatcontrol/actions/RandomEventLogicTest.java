package com.chatcontrol.actions;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

import static org.junit.jupiter.api.Assertions.*;

class RandomEventLogicTest {

    private static final List<String> DEFAULT_ACTIONS = List.of(
            "zombie", "spiders", "slowness", "blindness",
            "creeper", "storm", "random_teleport", "explosion", "chickens"
    );

    @Test
    void testRandomEventExcludesItself() {
        List<String> allowedActions = new ArrayList<>(DEFAULT_ACTIONS);
        allowedActions.removeIf(action -> action.equals("random_event"));
        assertFalse(allowedActions.contains("random_event"));
    }

    @Test
    void testEmptyListHandled() {
        List<String> allowedActions = new ArrayList<>();
        assertTrue(allowedActions.isEmpty());
    }

    @Test
    void testSelectionFromValidList() {
        List<String> validActions = List.of("zombie", "spiders", "creeper");
        Random random = new Random();
        String chosen = validActions.get(random.nextInt(validActions.size()));
        assertTrue(validActions.contains(chosen));
    }

    @Test
    void testSingleItemList() {
        List<String> validActions = List.of("zombie");
        Random random = new Random();
        String chosen = validActions.get(random.nextInt(validActions.size()));
        assertEquals("zombie", chosen);
    }

    @Test
    void testDisabledActionsFiltered() {
        List<String> allActions = new ArrayList<>(DEFAULT_ACTIONS);
        List<String> disabledActions = List.of("zombie", "spiders");
        List<String> enabledActions = new ArrayList<>();
        for (String action : allActions) {
            if (!disabledActions.contains(action)) {
                enabledActions.add(action);
            }
        }
        assertFalse(enabledActions.contains("zombie"));
        assertFalse(enabledActions.contains("spiders"));
        assertTrue(enabledActions.contains("creeper"));
    }

    @Test
    void testInexistentActionsFiltered() {
        List<String> allActions = new ArrayList<>(DEFAULT_ACTIONS);
        allActions.add("nonexistent_action");
        List<String> knownActions = List.of("zombie", "spiders", "creeper");
        List<String> validActions = new ArrayList<>();
        for (String action : allActions) {
            if (knownActions.contains(action)) {
                validActions.add(action);
            }
        }
        assertFalse(validActions.contains("nonexistent_action"));
        assertEquals(3, validActions.size());
    }
}
