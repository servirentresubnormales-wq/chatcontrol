package com.chatcontrol.actions;

import java.util.HashMap;
import java.util.Map;

public class ActionParameters {

    private final Map<String, String> params = new HashMap<>();

    public ActionParameters() {}

    public ActionParameters set(String key, String value) {
        params.put(key, value);
        return this;
    }

    public String get(String key) {
        return params.get(key);
    }

    public String get(String key, String defaultValue) {
        return params.getOrDefault(key, defaultValue);
    }

    public int getInt(String key, int defaultValue) {
        String value = params.get(key);
        if (value == null) return defaultValue;
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    public float getFloat(String key, float defaultValue) {
        String value = params.get(key);
        if (value == null) return defaultValue;
        try {
            return Float.parseFloat(value);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    public boolean getBoolean(String key, boolean defaultValue) {
        String value = params.get(key);
        if (value == null) return defaultValue;
        return Boolean.parseBoolean(value);
    }

    public boolean has(String key) {
        return params.containsKey(key);
    }

    public Map<String, String> getAll() {
        return new HashMap<>(params);
    }

    public static ActionParameters fromMap(Map<String, String> map) {
        ActionParameters params = new ActionParameters();
        if (map != null) {
            params.params.putAll(map);
        }
        return params;
    }
}
