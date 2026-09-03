package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.entity.EntityType;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

public class SpidersAction implements ActionHandler {

    @Override
    public String getName() { return "spiders"; }

    @Override
    public String getDescription() { return "Spawn multiple spiders in the player's current chunk"; }

    @Override
    public int getDefaultCooldownSeconds() {
        return ChatControlMod.getConfig().getActionCooldown("spiders");
    }

    @Override
    public boolean isDangerous() { return true; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] spiders: No target player");
            return false;
        }

        JsonObject cfg = ChatControlMod.getConfig().getActionConfig("spiders");
        int amount = cfg.has("amount") ? cfg.get("amount").getAsInt() : 4;

        amount = Math.min(amount, 20);

        SpawnConfig spawnConfig = new SpawnConfig(
                SpawnConfig.DEFAULT_MIN_DISTANCE,
                SpawnConfig.DEFAULT_MAX_ATTEMPTS
        );

        ChatControlMod.LOGGER.info("[ChatControl] Executing 'spiders' (x{}) for {} (chunk-restricted)",
                amount, target.getName().getString());

        boolean success = SpawnUtils.spawnMultipleEntitiesInChunk(EntityType.SPIDER, target, amount, spawnConfig);

        if (success) {
            target.sendMessage(net.minecraft.text.Text.literal("§c" + amount + " spiders appeared around you!"), false);
            ChatControlMod.LOGGER.info("[ChatControl] Spawned {} spiders in chunk of {}", amount, target.getName().getString());
        } else {
            ChatControlMod.LOGGER.warn("[ChatControl] Failed to spawn spiders in chunk of {}", target.getName().getString());
        }

        return success;
    }
}
