package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;

public class StormAction implements ActionHandler {

    @Override
    public String getName() { return "storm"; }

    @Override
    public String getDescription() { return "Start a thunderstorm"; }

    @Override
    public int getDefaultCooldownSeconds() {
        return ChatControlMod.getConfig().getActionCooldown("storm");
    }

    @Override
    public boolean isDangerous() { return false; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] storm: No target player");
            return false;
        }

        JsonObject cfg = ChatControlMod.getConfig().getActionConfig("storm");
        int duration = cfg.has("duration") ? cfg.get("duration").getAsInt() : 600;
        boolean thunder = cfg.has("thunder") ? cfg.get("thunder").getAsBoolean() : true;

        ServerWorld world = target.getServerWorld();

        ChatControlMod.LOGGER.info("[ChatControl] Executing 'storm' ({} ticks, thunder={})", duration, thunder);

        world.setWeather(0, duration, true, thunder);

        target.sendMessage(net.minecraft.text.Text.literal("§6A storm begins to brew..."), false);
        ChatControlMod.LOGGER.info("[ChatControl] Storm started in {} for {}", world.getRegistryKey().getValue(), target.getName().getString());
        return true;
    }
}
