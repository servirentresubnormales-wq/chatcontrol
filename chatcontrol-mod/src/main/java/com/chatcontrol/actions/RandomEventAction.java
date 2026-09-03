package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class RandomEventAction implements ActionHandler {

    private static final Random RANDOM = new Random();

    private static final List<String> DEFAULT_ACTIONS = List.of(
            "zombie", "spiders", "slowness", "blindness",
            "creeper", "storm", "random_teleport", "explosion", "chickens"
    );

    @Override
    public String getName() { return "random_event"; }

    @Override
    public String getDescription() { return "Execute a random action from the configured list"; }

    @Override
    public int getDefaultCooldownSeconds() {
        return ChatControlMod.getConfig().getActionCooldown("random_event");
    }

    @Override
    public boolean isDangerous() { return true; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] random_event: No target player");
            return false;
        }

        JsonObject cfg = ChatControlMod.getConfig().getActionConfig("random_event");

        List<String> allowedActions = new ArrayList<>();
        if (cfg.has("actions") && cfg.get("actions").isJsonArray()) {
            cfg.getAsJsonArray("actions").forEach(e -> allowedActions.add(e.getAsString()));
        }
        if (allowedActions.isEmpty()) {
            allowedActions.addAll(DEFAULT_ACTIONS);
        }

        allowedActions.removeIf(action -> action.equals("random_event"));

        List<String> validActions = new ArrayList<>();
        for (String actionName : allowedActions) {
            if (!ChatControlMod.getConfig().isActionEnabled(actionName)) {
                continue;
            }
            ActionHandler handler = ChatControlMod.getActionRegistry().getHandler(actionName);
            if (handler == null) {
                ChatControlMod.LOGGER.warn("[ChatControl] random_event: Unknown action '{}' in allowed list, skipping", actionName);
                continue;
            }
            validActions.add(actionName);
        }

        if (validActions.isEmpty()) {
            ChatControlMod.LOGGER.warn("[ChatControl] random_event: No valid actions available");
            return false;
        }

        String chosenAction = validActions.get(RANDOM.nextInt(validActions.size()));

        ChatControlMod.LOGGER.info("[ChatControl] random_event selected '{}' for {}", chosenAction, target.getName().getString());

        target.sendMessage(net.minecraft.text.Text.literal("§eA random event is coming..."), false);

        ActionHandler handler = ChatControlMod.getActionRegistry().getHandler(chosenAction);

        try {
            boolean success = handler.execute(server, target, params != null ? params : new ActionParameters());
            if (success) {
                ChatControlMod.LOGGER.info("[ChatControl] random_event executed '{}' successfully", chosenAction);
            }
            return success;
        } catch (Exception e) {
            ChatControlMod.LOGGER.error("[ChatControl] random_event: Error executing '{}': {}", chosenAction, e.getMessage());
            return false;
        }
    }
}
