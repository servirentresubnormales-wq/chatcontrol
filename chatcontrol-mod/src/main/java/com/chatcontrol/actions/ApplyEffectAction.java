package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import net.minecraft.entity.effect.StatusEffect;
import net.minecraft.entity.effect.StatusEffectInstance;
import net.minecraft.registry.Registries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import net.minecraft.util.Identifier;

public class ApplyEffectAction implements ActionHandler {

    @Override
    public String getName() {
        return "apply_effect";
    }

    @Override
    public String getDescription() {
        return "Apply a potion effect to the target player";
    }

    @Override
    public int getDefaultCooldownSeconds() {
        return 4;
    }

    @Override
    public boolean isDangerous() {
        return false;
    }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] apply_effect: No target player specified.");
            return false;
        }

        String effectId = params.get("effect", "minecraft:speed");
        int duration = params.getInt("duration", 200);
        int amplifier = params.getInt("amplifier", 0);

        if (duration < 1 || duration > 6000) {
            duration = Math.min(Math.max(duration, 1), 6000);
        }
        if (amplifier < 0 || amplifier > 10) {
            amplifier = Math.min(Math.max(amplifier, 0), 10);
        }

        Identifier identifier = Identifier.tryParse(effectId);
        if (identifier == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] apply_effect: Invalid effect ID: {}", effectId);
            return false;
        }

        var optEntry = Registries.STATUS_EFFECT.getEntry(identifier);
        if (optEntry.isEmpty()) {
            ChatControlMod.LOGGER.warn("[ChatControl] apply_effect: Unknown effect: {}", effectId);
            return false;
        }

        var effectEntry = optEntry.get();
        StatusEffectInstance instance = new StatusEffectInstance(effectEntry, duration, amplifier, false, true);
        target.addStatusEffect(instance);

        String effectName = effectEntry.value().getName().getString();
        target.sendMessage(Text.literal("§d[ChatControl] Applied " + effectName + " (level " + (amplifier + 1) + ") for " + (duration / 20) + "s"), false);
        ChatControlMod.LOGGER.info("[ChatControl] Applied {} to {} for {} ticks", effectId, target.getName().getString(), duration);
        return true;
    }
}
