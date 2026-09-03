package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import com.chatcontrol.network.ErrorCode;
import com.chatcontrol.protection.SafetyChecker;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

public class ActionExecutor {

    private final ActionRegistry registry;
    private final Map<String, Long> cooldowns = new ConcurrentHashMap<>();
    private final AtomicInteger actionsThisMinute = new AtomicInteger(0);
    private final AtomicLong lastMinuteReset = new AtomicLong(System.currentTimeMillis());
    private final AtomicLong lastGlobalAction = new AtomicLong(0);

    public ActionExecutor(ActionRegistry registry) {
        this.registry = registry;
    }

    public ActionResult execute(String actionName, MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (!ChatControlMod.getSystemState().isEnabled()) {
            return ActionResult.failure(ErrorCode.SYSTEM_DISABLED);
        }

        if (!SafetyChecker.isActionAllowed(actionName)) {
            ChatControlMod.LOGGER.warn("[ChatControl] Action '{}' is blocked by safety rules.", actionName);
            return ActionResult.failure(ErrorCode.ACTION_BLOCKED, "Action '" + actionName + "' is permanently blocked.");
        }

        ActionHandler handler = registry.getHandler(actionName);
        if (handler == null) {
            return ActionResult.failure(ErrorCode.UNKNOWN_ACTION, "Unknown action: " + actionName);
        }

        if (handler.isDangerous() && !ChatControlMod.getConfig().isAllowDangerousActions()) {
            return ActionResult.failure(ErrorCode.DANGEROUS_DISABLED, "Action '" + actionName + "' is dangerous and disabled in config.");
        }

        boolean bypassCooldown = handler.bypassCooldown();
        boolean bypassRateLimit = handler.bypassRateLimit();

        if (!bypassCooldown && !checkCooldown(actionName)) {
            long remaining = getCooldownRemaining(actionName);
            return ActionResult.failure(ErrorCode.ON_COOLDOWN, "Action '" + actionName + "' is on cooldown. Wait " + remaining + "s.");
        }

        int globalCooldown = ChatControlMod.getConfig().getGlobalCooldownSeconds();
        if (globalCooldown > 0 && !checkGlobalCooldown(globalCooldown)) {
            long elapsed = (System.currentTimeMillis() - lastGlobalAction.get()) / 1000;
            long remaining = Math.max(0, globalCooldown - elapsed);
            return ActionResult.failure(ErrorCode.GLOBAL_COOLDOWN, "Global cooldown active. Wait " + remaining + "s.");
        }

        if (!bypassRateLimit && !checkRateLimit()) {
            return ActionResult.failure(ErrorCode.RATE_LIMITED, "Rate limit exceeded. Try again later.");
        }

        if (params == null) {
            params = new ActionParameters();
        }

        if (!SafetyChecker.validateParams(actionName, params)) {
            return ActionResult.failure(ErrorCode.INVALID_PARAMS, "Invalid parameters for action '" + actionName + "'.");
        }

        try {
            boolean success = handler.execute(server, target, params);
            if (success) {
                if (!bypassCooldown) {
                    setCooldown(actionName);
                }
                lastGlobalAction.set(System.currentTimeMillis());
                if (!bypassRateLimit) {
                    incrementRateLimit();
                }
                ChatControlMod.getSystemState().incrementActionsExecuted();
                return ActionResult.success("Action '" + actionName + "' executed.");
            } else {
                return ActionResult.failure(ErrorCode.EXECUTION_ERROR, "Action '" + actionName + "' failed to execute.");
            }
        } catch (Exception e) {
            ChatControlMod.LOGGER.error("[ChatControl] Error executing action '{}': {}", actionName, e.getMessage(), e);
            return ActionResult.failure(ErrorCode.EXECUTION_ERROR, "Error executing action: " + e.getMessage());
        }
    }

    private boolean checkCooldown(String actionName) {
        Long lastUse = cooldowns.get(actionName);
        if (lastUse == null) return true;
        long elapsed = (System.currentTimeMillis() - lastUse) / 1000;
        int cooldown = ChatControlMod.getConfig().getActionCooldown(actionName);
        return elapsed >= cooldown;
    }

    private long getCooldownRemaining(String actionName) {
        Long lastUse = cooldowns.get(actionName);
        if (lastUse == null) return 0;
        int cooldown = ChatControlMod.getConfig().getActionCooldown(actionName);
        long elapsed = (System.currentTimeMillis() - lastUse) / 1000;
        return Math.max(0, cooldown - elapsed);
    }

    private void setCooldown(String actionName) {
        cooldowns.put(actionName, System.currentTimeMillis());
    }

    private boolean checkGlobalCooldown(int globalCooldownSeconds) {
        long elapsed = (System.currentTimeMillis() - lastGlobalAction.get()) / 1000;
        return elapsed >= globalCooldownSeconds;
    }

    private boolean checkRateLimit() {
        resetMinuteIfNeeded();
        return actionsThisMinute.get() < ChatControlMod.getConfig().getMaxActionsPerMinute();
    }

    private void incrementRateLimit() {
        actionsThisMinute.incrementAndGet();
    }

    private void resetMinuteIfNeeded() {
        long now = System.currentTimeMillis();
        long lastReset = lastMinuteReset.get();
        if (now - lastReset >= 60000) {
            if (lastMinuteReset.compareAndSet(lastReset, now)) {
                actionsThisMinute.set(0);
            }
        }
    }
}
