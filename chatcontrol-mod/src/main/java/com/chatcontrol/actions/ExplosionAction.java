package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.world.World;

public class ExplosionAction implements ActionHandler {

    @Override
    public String getName() { return "explosion"; }

    @Override
    public String getDescription() { return "Create an explosion in the player's current chunk"; }

    @Override
    public int getDefaultCooldownSeconds() {
        return ChatControlMod.getConfig().getActionCooldown("explosion");
    }

    @Override
    public boolean isDangerous() { return true; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] explosion: No target player");
            return false;
        }

        JsonObject cfg = ChatControlMod.getConfig().getActionConfig("explosion");
        float radius = cfg.has("radius") ? cfg.get("radius").getAsFloat() : 3.0f;
        boolean fire = cfg.has("fire") ? cfg.get("fire").getAsBoolean() : false;
        boolean destroyBlocks = cfg.has("destroy-blocks") ? cfg.get("destroy-blocks").getAsBoolean() : false;

        radius = Math.min(radius, 10.0f);

        World.ExplosionSourceType sourceType = destroyBlocks
                ? World.ExplosionSourceType.BLOCK
                : World.ExplosionSourceType.NONE;

        SpawnConfig spawnConfig = new SpawnConfig(
                SpawnConfig.DEFAULT_MIN_DISTANCE,
                SpawnConfig.DEFAULT_MAX_ATTEMPTS
        );

        ChatControlMod.LOGGER.info("[ChatControl] Executing 'explosion' for {} power={} (chunk-restricted)",
                target.getName().getString(), radius);

        boolean success = SpawnUtils.createExplosionInChunk(target, radius, fire, sourceType, spawnConfig);

        if (success) {
            target.sendMessage(net.minecraft.text.Text.literal("§4BOOM!"), false);
            ChatControlMod.LOGGER.info("[ChatControl] Explosion created in chunk of {}", target.getName().getString());
        } else {
            ChatControlMod.LOGGER.warn("[ChatControl] Failed to create explosion in chunk of {}", target.getName().getString());
        }

        return success;
    }
}
