package com.chatcontrol.protection;

import com.chatcontrol.actions.ActionParameters;
import com.chatcontrol.ChatControlMod;

import java.util.Set;

public class SafetyChecker {

    private static final Set<String> BLOCKED_ACTIONS = Set.of(
            "stop_server",
            "op_player",
            "deop_player",
            "ban_player",
            "whitelist"
    );

    private static final Set<String> DANGEROUS_ACTIONS = Set.of(
            "summon_mob"
    );

    public static boolean isActionAllowed(String actionName) {
        if (BLOCKED_ACTIONS.contains(actionName)) {
            ChatControlMod.LOGGER.warn("[ChatControl] Action '{}' is permanently blocked.", actionName);
            return false;
        }

        if (DANGEROUS_ACTIONS.contains(actionName) && !ChatControlMod.getConfig().isAllowDangerousActions()) {
            return false;
        }

        return true;
    }

    public static boolean validateParams(String actionName, ActionParameters params) {
        if (params == null) return true;

        switch (actionName) {
            case "give_item" -> {
                String item = params.get("item");
                if (item != null && isBlockedItem(item)) {
                    return false;
                }
                int count = params.getInt("count", 1);
                if (count < 1 || count > ChatControlMod.getConfig().getMaxItemsPerAction()) {
                    return false;
                }
            }
            case "summon_mob" -> {
                int count = params.getInt("count", 1);
                if (count < 1 || count > ChatControlMod.getConfig().getMaxMobsPerAction()) {
                    return false;
                }
            }
            case "apply_effect" -> {
                String effect = params.get("effect");
                if (effect != null && isBlockedEffect(effect)) {
                    return false;
                }
                int duration = params.getInt("duration", 200);
                if (duration < 1 || duration > 6000) {
                    return false;
                }
                int amplifier = params.getInt("amplifier", 0);
                if (amplifier < 0 || amplifier > 10) {
                    return false;
                }
            }
            case "spiders" -> {
                int amount = params.getInt("amount", 4);
                if (amount < 1 || amount > 20) {
                    return false;
                }
                int radius = params.getInt("radius", 5);
                if (radius < 1 || radius > 50) {
                    return false;
                }
            }
            case "explosion" -> {
                float radius = params.getFloat("radius", 3.0f);
                if (radius < 0.5f || radius > 10.0f) {
                    return false;
                }
            }
            case "random_teleport" -> {
                int radius = params.getInt("radius", 30);
                if (radius < 1 || radius > 200) {
                    return false;
                }
            }
            case "chickens" -> {
                int amount = params.getInt("amount", 1);
                if (amount < 1 || amount > 10) {
                    return false;
                }
            }
            case "slowness" -> {
                int duration = params.getInt("duration", 200);
                if (duration < 1 || duration > 6000) {
                    return false;
                }
                int amplifier = params.getInt("amplifier", 1);
                if (amplifier < 0 || amplifier > 10) {
                    return false;
                }
            }
            case "blindness" -> {
                int duration = params.getInt("duration", 160);
                if (duration < 1 || duration > 6000) {
                    return false;
                }
                int amplifier = params.getInt("amplifier", 0);
                if (amplifier < 0 || amplifier > 10) {
                    return false;
                }
            }
        }

        return true;
    }

    private static boolean isBlockedItem(String itemId) {
        return itemId.contains("command_block") ||
               itemId.contains("barrier") ||
               itemId.contains("bedrock") ||
               itemId.contains("end_portal") ||
               itemId.contains("structure_block");
    }

    private static boolean isBlockedEffect(String effectId) {
        return effectId.contains("instant_damage") ||
               effectId.contains("wither");
    }

    public static boolean isCommandSafe(String command) {
        if (command == null || command.isEmpty()) return false;

        String lower = command.toLowerCase();
        return !lower.contains("stop") &&
               !lower.contains("op ") &&
               !lower.contains("deop ") &&
               !lower.contains("ban ") &&
               !lower.contains("whitelist") &&
               !lower.contains("kill @a") &&
               !lower.contains("/fill ") &&
               !lower.contains("setblock ") &&
               !lower.contains("summon tnt");
    }
}
