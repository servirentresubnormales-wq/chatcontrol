package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.entity.EntityType;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

public class CreeperAction implements ActionHandler {

    @Override
    public String getName() { return "creeper"; }

    @Override
    public String getDescription() { return "Spawn a creeper in the player's current chunk"; }

    @Override
    public int getDefaultCooldownSeconds() {
        return ChatControlMod.getConfig().getActionCooldown("creeper");
    }

    @Override
    public boolean isDangerous() { return true; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] creeper: No target player");
            return false;
        }

        SpawnConfig spawnConfig = new SpawnConfig(
                SpawnConfig.DEFAULT_MIN_DISTANCE,
                SpawnConfig.DEFAULT_MAX_ATTEMPTS
        );

        ChatControlMod.LOGGER.info("[ChatControl] Executing 'creeper' for {} (chunk-restricted)",
                target.getName().getString());

        boolean success = SpawnUtils.spawnEntityInChunk(EntityType.CREEPER, target, spawnConfig);

        if (success) {
            target.sendMessage(net.minecraft.text.Text.literal("§4You hear a hissing sound..."), false);
            ChatControlMod.LOGGER.info("[ChatControl] Spawned creeper in chunk of {}", target.getName().getString());
        } else {
            ChatControlMod.LOGGER.warn("[ChatControl] Failed to spawn creeper in chunk of {}", target.getName().getString());
        }

        return success;
    }
}
