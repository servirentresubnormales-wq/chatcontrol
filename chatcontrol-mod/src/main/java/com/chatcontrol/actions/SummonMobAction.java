package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityType;
import net.minecraft.registry.Registries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import net.minecraft.util.Identifier;

public class SummonMobAction implements ActionHandler {

    @Override
    public String getName() {
        return "summon_mob";
    }

    @Override
    public String getDescription() {
        return "Summon mobs near the target player";
    }

    @Override
    public int getDefaultCooldownSeconds() {
        return 5;
    }

    @Override
    public boolean isDangerous() {
        return true;
    }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] summon_mob: No target player specified.");
            return false;
        }

        String mobId = params.get("mob", "minecraft:zombie");
        int count = params.getInt("count", 1);
        int maxMobs = ChatControlMod.getConfig().getMaxMobsPerAction();

        if (count < 1 || count > maxMobs) {
            count = Math.min(Math.max(count, 1), maxMobs);
        }

        Identifier identifier = Identifier.tryParse(mobId);
        if (identifier == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] summon_mob: Invalid mob ID: {}", mobId);
            return false;
        }

        EntityType<?> entityType = Registries.ENTITY_TYPE.get(identifier);
        if (entityType == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] summon_mob: Unknown mob type: {}", mobId);
            return false;
        }

        int spawned = 0;
        for (int i = 0; i < count; i++) {
            double offsetX = (target.getWorld().getRandom().nextDouble() - 0.5) * 6.0;
            double offsetZ = (target.getWorld().getRandom().nextDouble() - 0.5) * 6.0;

            Entity entity = entityType.create(target.getWorld());
            if (entity != null) {
                entity.setPosition(target.getX() + offsetX, target.getY(), target.getZ() + offsetZ);
                target.getWorld().spawnEntity(entity);
                spawned++;
            }
        }

        if (spawned > 0) {
            target.sendMessage(Text.literal("§c[ChatControl] " + spawned + "x " + entityType.getName().getString() + " spawned near you!"), false);
            ChatControlMod.LOGGER.info("[ChatControl] Summoned {}x {} near {}", spawned, mobId, target.getName().getString());
            return true;
        }

        return false;
    }
}
