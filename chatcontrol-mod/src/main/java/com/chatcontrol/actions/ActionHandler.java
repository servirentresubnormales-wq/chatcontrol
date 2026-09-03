package com.chatcontrol.actions;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

public interface ActionHandler {

    String getName();

    String getDescription();

    default int getDefaultCooldownSeconds() {
        return 5;
    }

    default boolean isDangerous() {
        return false;
    }

    default boolean bypassCooldown() {
        return false;
    }

    default boolean bypassRateLimit() {
        return false;
    }

    boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params);
}
