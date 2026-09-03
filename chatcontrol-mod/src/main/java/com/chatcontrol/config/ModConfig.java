package com.chatcontrol.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.chatcontrol.ChatControlMod;
import net.fabricmc.loader.api.FabricLoader;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

public class ModConfig {

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Path CONFIG_PATH = FabricLoader.getInstance()
            .getConfigDir().resolve("chatcontrol.json");

    private boolean enabled = false;
    private boolean autoStart = false;
    private boolean networkEnabled = true;
    private int networkPort = 8765;
    private boolean loggingEnabled = true;
    private int maxActionsPerMinute = 30;
    private int defaultCooldownSeconds = 5;
    private int globalCooldownSeconds = 1;
    private boolean allowDangerousActions = false;
    private int maxItemsPerAction = 64;
    private int maxMobsPerAction = 10;

    private AuthenticationConfig authentication = new AuthenticationConfig();

    private Map<String, JsonObject> actionConfigs = new HashMap<>();

    public static class AuthenticationConfig {
        private boolean enabled = false;
        private String token = "";
        private int timeoutSeconds = 10;
        private int maxFailedAttempts = 5;
        private int rateLimitWindowSeconds = 300;

        public boolean isEnabled() { return enabled; }
        public void setEnabled(boolean enabled) { this.enabled = enabled; }
        public String getToken() { return token; }
        public void setToken(String token) { this.token = token; }
        public int getTimeoutSeconds() { return timeoutSeconds; }
        public void setTimeoutSeconds(int timeoutSeconds) { this.timeoutSeconds = timeoutSeconds; }
        public int getMaxFailedAttempts() { return maxFailedAttempts; }
        public void setMaxFailedAttempts(int maxFailedAttempts) { this.maxFailedAttempts = maxFailedAttempts; }
        public int getRateLimitWindowSeconds() { return rateLimitWindowSeconds; }
        public void setRateLimitWindowSeconds(int rateLimitWindowSeconds) { this.rateLimitWindowSeconds = rateLimitWindowSeconds; }
    }

    public static ModConfig load() {
        ModConfig config = new ModConfig();

        if (Files.exists(CONFIG_PATH)) {
            try (Reader reader = Files.newBufferedReader(CONFIG_PATH)) {
                config = GSON.fromJson(reader, ModConfig.class);
                if (config.actionConfigs == null) {
                    config.actionConfigs = new HashMap<>();
                }
                ChatControlMod.LOGGER.info("[ChatControl] Config loaded from {}", CONFIG_PATH);
            } catch (IOException e) {
                ChatControlMod.LOGGER.error("[ChatControl] Failed to load config, using defaults", e);
            }
        } else {
            config.actionConfigs = createActionDefaults();
            config.save();
            ChatControlMod.LOGGER.info("[ChatControl] Default config created at {}", CONFIG_PATH);
        }

        return config;
    }

    public void save() {
        try (Writer writer = Files.newBufferedWriter(CONFIG_PATH)) {
            GSON.toJson(this, writer);
        } catch (IOException e) {
            ChatControlMod.LOGGER.error("[ChatControl] Failed to save config", e);
        }
    }

    public void reload() {
        ModConfig loaded = load();
        this.enabled = loaded.enabled;
        this.autoStart = loaded.autoStart;
        this.networkEnabled = loaded.networkEnabled;
        this.networkPort = loaded.networkPort;
        this.loggingEnabled = loaded.loggingEnabled;
        this.maxActionsPerMinute = loaded.maxActionsPerMinute;
        this.defaultCooldownSeconds = loaded.defaultCooldownSeconds;
        this.globalCooldownSeconds = loaded.globalCooldownSeconds;
        this.allowDangerousActions = loaded.allowDangerousActions;
        this.maxItemsPerAction = loaded.maxItemsPerAction;
        this.maxMobsPerAction = loaded.maxMobsPerAction;
        this.authentication = loaded.authentication;
        this.actionConfigs = loaded.actionConfigs;
        ChatControlMod.LOGGER.info("[ChatControl] Config reloaded.");
    }

    public JsonObject getActionConfig(String actionName) {
        return actionConfigs.getOrDefault(actionName, new JsonObject());
    }

    public boolean isActionEnabled(String actionName) {
        JsonObject cfg = getActionConfig(actionName);
        return cfg.has("enabled") ? cfg.get("enabled").getAsBoolean() : true;
    }

    public int getActionCooldown(String actionName) {
        JsonObject cfg = getActionConfig(actionName);
        return cfg.has("cooldown") ? cfg.get("cooldown").getAsInt() : defaultCooldownSeconds;
    }

    private static Map<String, JsonObject> createActionDefaults() {
        Map<String, JsonObject> defaults = new HashMap<>();

        defaults.put("zombie", createJsonObj(true, 10, "radius", 4));
        defaults.put("spiders", createJsonObj(true, 15, "amount", 4, "radius", 5));
        defaults.put("slowness", createJsonObj(true, 20, "duration", 200, "amplifier", 1));
        defaults.put("blindness", createJsonObj(true, 20, "duration", 160, "amplifier", 0));
        defaults.put("creeper", createJsonObj(true, 30, "radius", 4));
        defaults.put("storm", createJsonObj(true, 60, "duration", 600, "thunder", true));
        defaults.put("random_teleport", createJsonObj(true, 60, "radius", 30, "max-attempts", 20));
        defaults.put("explosion", createJsonObj(true, 30, "radius", 3.0, "fire", false, "destroy-blocks", false));
        defaults.put("random_event", createJsonObj(true, 60));
        defaults.put("chickens", createChickensConfig());

        return defaults;
    }

    private static JsonObject createJsonObj(boolean enabled, int cooldown, Object... keyValues) {
        JsonObject obj = new JsonObject();
        obj.addProperty("enabled", enabled);
        obj.addProperty("cooldown", cooldown);
        for (int i = 0; i < keyValues.length; i += 2) {
            String key = (String) keyValues[i];
            Object value = keyValues[i + 1];
            if (value instanceof Boolean b) obj.addProperty(key, b);
            else if (value instanceof Integer i2) obj.addProperty(key, i2);
            else if (value instanceof Double d) obj.addProperty(key, d);
            else if (value instanceof String s) obj.addProperty(key, s);
        }
        return obj;
    }

    private static JsonObject createChickensConfig() {
        JsonObject obj = new JsonObject();
        obj.addProperty("enabled", true);
        obj.addProperty("amount", 1);
        obj.addProperty("radius", 4);
        obj.addProperty("bypass-cooldown", true);
        obj.addProperty("bypass-rate-limit", true);
        return obj;
    }

    // --- Getters/Setters ---

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }

    public boolean isAutoStart() { return autoStart; }
    public void setAutoStart(boolean autoStart) { this.autoStart = autoStart; }

    public boolean isNetworkEnabled() { return networkEnabled; }
    public void setNetworkEnabled(boolean networkEnabled) { this.networkEnabled = networkEnabled; }

    public int getNetworkPort() { return networkPort; }
    public void setNetworkPort(int networkPort) { this.networkPort = networkPort; }

    public boolean isLoggingEnabled() { return loggingEnabled; }
    public void setLoggingEnabled(boolean loggingEnabled) { this.loggingEnabled = loggingEnabled; }

    public int getMaxActionsPerMinute() { return maxActionsPerMinute; }
    public void setMaxActionsPerMinute(int maxActionsPerMinute) { this.maxActionsPerMinute = maxActionsPerMinute; }

    public int getDefaultCooldownSeconds() { return defaultCooldownSeconds; }
    public void setDefaultCooldownSeconds(int defaultCooldownSeconds) { this.defaultCooldownSeconds = defaultCooldownSeconds; }

    public int getGlobalCooldownSeconds() { return globalCooldownSeconds; }
    public void setGlobalCooldownSeconds(int globalCooldownSeconds) { this.globalCooldownSeconds = globalCooldownSeconds; }

    public boolean isAllowDangerousActions() { return allowDangerousActions; }
    public void setAllowDangerousActions(boolean allowDangerousActions) { this.allowDangerousActions = allowDangerousActions; }

    public int getMaxItemsPerAction() { return maxItemsPerAction; }
    public void setMaxItemsPerAction(int maxItemsPerAction) { this.maxItemsPerAction = maxItemsPerAction; }

    public int getMaxMobsPerAction() { return maxMobsPerAction; }
    public void setMaxMobsPerAction(int maxMobsPerAction) { this.maxMobsPerAction = maxMobsPerAction; }

    public AuthenticationConfig getAuthentication() { return authentication; }
    public void setAuthentication(AuthenticationConfig authentication) { this.authentication = authentication; }

    public Map<String, JsonObject> getActionConfigs() { return actionConfigs; }
}
