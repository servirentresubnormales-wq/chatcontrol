package com.chatcontrol.events;

import com.chatcontrol.ChatControlMod;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class EventRegistry {

    private final Map<String, EventDefinition> events = new HashMap<>();
    private final Map<String, Long> lastExecution = new ConcurrentHashMap<>();

    public void register(EventDefinition event) {
        events.put(event.getName(), event);
        ChatControlMod.LOGGER.info("[ChatControl] Registered event: {}", event.getName());
    }

    public EventDefinition getEvent(String name) {
        return events.get(name);
    }

    public Collection<EventDefinition> getRegisteredEvents() {
        return Collections.unmodifiableCollection(events.values());
    }

    public Collection<String> getEventNames() {
        return Collections.unmodifiableSet(events.keySet());
    }

    public boolean isOnCooldown(String eventName) {
        Long lastExec = lastExecution.get(eventName);
        if (lastExec == null) return false;

        EventDefinition event = events.get(eventName);
        if (event == null) return false;

        long elapsed = (System.currentTimeMillis() - lastExec) / 1000;
        return elapsed < event.getCooldownSeconds();
    }

    public long getCooldownRemaining(String eventName) {
        Long lastExec = lastExecution.get(eventName);
        if (lastExec == null) return 0;

        EventDefinition event = events.get(eventName);
        if (event == null) return 0;

        long elapsed = (System.currentTimeMillis() - lastExec) / 1000;
        return Math.max(0, event.getCooldownSeconds() - elapsed);
    }

    public boolean executeEvent(String eventName, MinecraftServer server, ServerPlayerEntity target, String source) {
        EventDefinition event = events.get(eventName);
        if (event == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] Unknown event: {}", eventName);
            return false;
        }

        if (!event.isEnabled()) {
            ChatControlMod.LOGGER.warn("[ChatControl] Event '{}' is disabled.", eventName);
            return false;
        }

        if (isOnCooldown(eventName)) {
            ChatControlMod.LOGGER.info("[ChatControl] Event '{}' is on cooldown ({}s remaining).", eventName, getCooldownRemaining(eventName));
            return false;
        }

        boolean success = event.execute(server, target, source);
        if (success) {
            lastExecution.put(eventName, System.currentTimeMillis());
            ChatControlMod.LOGGER.info("[ChatControl] Event '{}' executed successfully by {}", eventName, source);
        }

        return success;
    }

    public void clear() {
        lastExecution.clear();
        ChatControlMod.LOGGER.info("[ChatControl] Event registry cleared.");
    }

    public void tick(MinecraftServer server) {
        // Future: auto-trigger events, periodic events, etc.
    }
}
