package com.chatcontrol.actions;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public class ActionRegistry {

    private final Map<String, ActionHandler> handlers = new HashMap<>();

    public void register(ActionHandler handler) {
        handlers.put(handler.getName(), handler);
    }

    public ActionHandler getHandler(String name) {
        return handlers.get(name);
    }

    public Set<String> getRegisteredNames() {
        return handlers.keySet();
    }

    public Map<String, ActionHandler> getAllHandlers() {
        return new HashMap<>(handlers);
    }

    public boolean isRegistered(String name) {
        return handlers.containsKey(name);
    }
}
