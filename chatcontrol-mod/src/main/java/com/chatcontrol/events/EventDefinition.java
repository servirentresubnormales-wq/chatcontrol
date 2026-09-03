package com.chatcontrol.events;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

public interface EventDefinition {

    String getName();

    String getDescription();

    int getCooldownSeconds();

    default int getWeight() {
        return 10;
    }

    default boolean isEnabled() {
        return true;
    }

    boolean execute(MinecraftServer server, ServerPlayerEntity target, String source);
}
