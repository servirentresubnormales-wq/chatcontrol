package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.entity.EntityType;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

public class ZombieAction implements ActionHandler {

    @Override
    public String getName() { return "zombie"; }

    @Override
    public String getDescription() { return "Spawn a zombie in the player's current chunk"; }

    @Override
    public int getDefaultCooldownSeconds() {
        return ChatControlMod.getConfig().getActionCooldown("zombie");
    }

    @Override
    public boolean isDangerous() { return true; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] zombie: No target player");
            return false;
        }

        JsonObject cfg = ChatControlMod.getConfig().getActionConfig("zombie");
        int radius = cfg.has("radius") ? cfg.get("radius").getAsInt() : 4;

        SpawnConfig spawnConfig = new SpawnConfig(
                SpawnConfig.DEFAULT_MIN_DISTANCE,
                SpawnConfig.DEFAULT_MAX_ATTEMPTS
        );

        ChatControlMod.LOGGER.info("[ChatControl] Executing 'zombie' for {} (chunk-restricted)",
                target.getName().getString());

        boolean success = SpawnUtils.spawnEntityInChunk(EntityType.ZOMBIE, target, spawnConfig);

        if (success) {
            target.sendMessage(net.minecraft.text.Text.literal("§cA zombie appeared near you!"), false);
            ChatControlMod.LOGGER.info("[ChatControl] Spawned zombie in chunk of {}", target.getName().getString());
        } else {
            ChatControlMod.LOGGER.warn("[ChatControl] Failed to spawn zombie in chunk of {}", target.getName().getString());
        }

        return success;
    }
}
