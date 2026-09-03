package com.chatcontrol.network;

public enum ErrorCode {

    INVALID_JSON("INVALID_JSON", "Invalid JSON format"),
    MISSING_ACTION("MISSING_ACTION", "Missing 'action' field"),
    UNKNOWN_ACTION("UNKNOWN_ACTION", "Unknown action"),
    ACTION_DISABLED("ACTION_DISABLED", "Action is disabled"),
    ACTION_BLOCKED("ACTION_BLOCKED", "Action is permanently blocked"),
    DANGEROUS_DISABLED("DANGEROUS_DISABLED", "Dangerous actions are disabled in config"),
    PLAYER_NOT_FOUND("PLAYER_NOT_FOUND", "Player not found"),
    NO_PLAYERS_ONLINE("NO_PLAYERS_ONLINE", "No players online"),
    INVALID_PARAMS("INVALID_PARAMS", "Invalid parameters for action"),
    ON_COOLDOWN("ON_COOLDOWN", "Action is on cooldown"),
    RATE_LIMITED("RATE_LIMITED", "Rate limit exceeded"),
    GLOBAL_COOLDOWN("GLOBAL_COOLDOWN", "Global cooldown active"),
    SYSTEM_DISABLED("SYSTEM_DISABLED", "System is not active"),
    EXECUTION_ERROR("EXECUTION_ERROR", "Error executing action"),
    COMMAND_TIMEOUT("COMMAND_TIMEOUT", "Command timed out"),
    THREAD_POOL_FULL("THREAD_POOL_FULL", "Server busy, try again later"),
    MISSING_PLAYER("MISSING_PLAYER", "This command requires a player"),
    UNAUTHORIZED("UNAUTHORIZED", "Unauthorized"),
    INVALID_PROTOCOL("INVALID_PROTOCOL", "Invalid or unsupported protocol version");

    private final String code;
    private final String defaultMessage;

    ErrorCode(String code, String defaultMessage) {
        this.code = code;
        this.defaultMessage = defaultMessage;
    }

    public String getCode() {
        return code;
    }

    public String getDefaultMessage() {
        return defaultMessage;
    }

    public static ErrorCode fromCode(String code) {
        for (ErrorCode error : values()) {
            if (error.code.equals(code)) {
                return error;
            }
        }
        return null;
    }
}
