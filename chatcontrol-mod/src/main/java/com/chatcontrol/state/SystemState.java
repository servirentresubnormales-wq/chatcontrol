package com.chatcontrol.state;

import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

public class SystemState {

    private final AtomicBoolean enabled = new AtomicBoolean(false);
    private final AtomicLong enabledAt = new AtomicLong(0);
    private final AtomicLong totalActionsExecuted = new AtomicLong(0);
    private volatile UUID lastActionUser = null;

    public boolean isEnabled() {
        return enabled.get();
    }

    public void setEnabled(boolean enabled) {
        this.enabled.set(enabled);
        if (enabled) {
            this.enabledAt.set(System.currentTimeMillis());
        }
    }

    public long getEnabledAt() {
        return enabledAt.get();
    }

    public long getUptimeMs() {
        if (!enabled.get() || enabledAt.get() == 0) return 0;
        return System.currentTimeMillis() - enabledAt.get();
    }

    public long getTotalActionsExecuted() {
        return totalActionsExecuted.get();
    }

    public void incrementActionsExecuted() {
        totalActionsExecuted.incrementAndGet();
    }

    public UUID getLastActionUser() {
        return lastActionUser;
    }

    public void setLastActionUser(UUID lastActionUser) {
        this.lastActionUser = lastActionUser;
    }

    public void reset() {
        enabled.set(false);
        enabledAt.set(0);
        totalActionsExecuted.set(0);
        lastActionUser = null;
    }
}
