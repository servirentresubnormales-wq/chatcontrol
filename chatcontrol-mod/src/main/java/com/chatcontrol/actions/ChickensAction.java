package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.entity.EntityType;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

public class ChickensAction implements ActionHandler {

    @Override
    public String getName() { return "chickens"; }

    @Override
    public String getDescription() { return "Spawn chickens in the player's current chunk (bypasses cooldown)"; }

    @Override
    public int getDefaultCooldownSeconds() { return 0; }

    @Override
    public boolean isDangerous() { return false; }

    @Override
    public boolean bypassCooldown() { return true; }

    @Override
    public boolean bypassRateLimit() { return true; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            return false;
        }

        JsonObject cfg = ChatControlMod.getConfig().getActionConfig("chickens");
        int amount = cfg.has("amount") ? cfg.get("amount").getAsInt() : 1;

        amount = Math.min(amount, 10);

        SpawnConfig spawnConfig = new SpawnConfig(
                SpawnConfig.DEFAULT_MIN_DISTANCE,
                SpawnConfig.DEFAULT_MAX_ATTEMPTS
        );

        boolean success = SpawnUtils.spawnMultipleEntitiesInChunk(EntityType.CHICKEN, target, amount, spawnConfig);

        if (success) {
            target.sendMessage(net.minecraft.text.Text.literal("§aBawk bawk!"), false);
        }

        return success;
    }
}
