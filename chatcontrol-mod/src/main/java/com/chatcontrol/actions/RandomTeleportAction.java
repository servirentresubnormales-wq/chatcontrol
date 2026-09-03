package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

public class RandomTeleportAction implements ActionHandler {

    @Override
    public String getName() { return "random_teleport"; }

    @Override
    public String getDescription() { return "Teleport the player to a random safe location in their current chunk"; }

    @Override
    public int getDefaultCooldownSeconds() {
        return ChatControlMod.getConfig().getActionCooldown("random_teleport");
    }

    @Override
    public boolean isDangerous() { return false; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] random_teleport: No target player");
            return false;
        }

        JsonObject cfg = ChatControlMod.getConfig().getActionConfig("random_teleport");
        int maxAttempts = cfg.has("max-attempts") ? cfg.get("max-attempts").getAsInt() : 20;

        SpawnConfig spawnConfig = new SpawnConfig(
                SpawnConfig.DEFAULT_MIN_DISTANCE,
                maxAttempts
        );

        ChatControlMod.LOGGER.info("[ChatControl] Executing 'random_teleport' for {} (chunk-restricted, maxAttempts={})",
                target.getName().getString(), maxAttempts);

        boolean success = SpawnUtils.teleportToChunkPosition(target, spawnConfig);

        if (success) {
            target.sendMessage(net.minecraft.text.Text.literal("§bYou've been teleported!"), false);
            ChatControlMod.LOGGER.info("[ChatControl] Teleported {} within their chunk",
                    target.getName().getString());
        } else {
            target.sendMessage(net.minecraft.text.Text.literal("§eCouldn't find a safe location to teleport!"), false);
            ChatControlMod.LOGGER.warn("[ChatControl] Failed to find safe teleport position in chunk of {}",
                    target.getName().getString());
        }

        return success;
    }
}
