package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.google.gson.JsonObject;
import net.minecraft.entity.effect.StatusEffectInstance;
import net.minecraft.entity.effect.StatusEffects;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

public class BlindnessAction implements ActionHandler {

    @Override
    public String getName() { return "blindness"; }

    @Override
    public String getDescription() { return "Apply blindness to the player"; }

    @Override
    public int getDefaultCooldownSeconds() {
        return ChatControlMod.getConfig().getActionCooldown("blindness");
    }

    @Override
    public boolean isDangerous() { return false; }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] blindness: No target player");
            return false;
        }

        JsonObject cfg = ChatControlMod.getConfig().getActionConfig("blindness");
        int duration = cfg.has("duration") ? cfg.get("duration").getAsInt() : 160;
        int amplifier = cfg.has("amplifier") ? cfg.get("amplifier").getAsInt() : 0;

        ChatControlMod.LOGGER.info("[ChatControl] Executing 'blindness' on {}", target.getName().getString());

        StatusEffectInstance effect = new StatusEffectInstance(StatusEffects.BLINDNESS, duration, amplifier, false, true);
        target.addStatusEffect(effect);

        target.sendMessage(net.minecraft.text.Text.literal("§8You can't see anything!"), false);
        ChatControlMod.LOGGER.info("[ChatControl] Applied blindness to {} ({} ticks)", target.getName().getString(), duration);
        return true;
    }
}
