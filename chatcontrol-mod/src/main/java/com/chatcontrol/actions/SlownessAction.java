package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.entity.effect.StatusEffectInstance;
import net.minecraft.entity.effect.StatusEffects;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

public class SlownessAction implements ActionHandler {

    @Override
    public String getName() { return "slowness"; }

    @Override
    public String getDescription() { return "Apply slowness to the player"; }

    @Override
    public int getDefaultCooldownSeconds() {
        return ChatControlMod.getConfig().getActionCooldown("slowness");
    }

    @Override
    public boolean isDangerous() { return false; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] slowness: No target player");
            return false;
        }

        JsonObject cfg = ChatControlMod.getConfig().getActionConfig("slowness");
        int duration = cfg.has("duration") ? cfg.get("duration").getAsInt() : 200;
        int amplifier = cfg.has("amplifier") ? cfg.get("amplifier").getAsInt() : 1;

        ChatControlMod.LOGGER.info("[ChatControl] Executing 'slowness' on {}", target.getName().getString());

        StatusEffectInstance effect = new StatusEffectInstance(StatusEffects.SLOWNESS, duration, amplifier, false, true);
        target.addStatusEffect(effect);

        target.sendMessage(net.minecraft.text.Text.literal("§9You feel sluggish..."), false);
        ChatControlMod.LOGGER.info("[ChatControl] Applied slowness to {} ({} ticks, amplifier {})", target.getName().getString(), duration, amplifier);
        return true;
    }
}
