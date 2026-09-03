package com.chatcontrol.network;

import com.google.gson.JsonObject;

public class BridgeResponse {

    private boolean success;
    private String action;
    private String message;
    private ErrorCode errorCode;
    private String target;
    private String source;
    private String user;
    private String messageId;
    private long executionTimeMs;
    private int protocolVersion;
    private JsonObject metadata;

    public BridgeResponse() {
        this.protocolVersion = ProtocolConstants.PROTOCOL_VERSION;
    }

    public static BridgeResponse success(String action, String target, long executionTimeMs) {
        BridgeResponse response = new BridgeResponse();
        response.success = true;
        response.action = action;
        response.target = target;
        response.message = "Action '" + action + "' executed.";
        response.executionTimeMs = executionTimeMs;
        return response;
    }

    public static BridgeResponse error(ErrorCode errorCode, String message) {
        BridgeResponse response = new BridgeResponse();
        response.success = false;
        response.errorCode = errorCode;
        response.message = message != null ? message : errorCode.getDefaultMessage();
        return response;
    }

    public static BridgeResponse error(ErrorCode errorCode) {
        return error(errorCode, null);
    }

    public JsonObject toJson() {
        JsonObject json = new JsonObject();
        json.addProperty("success", success);
        json.addProperty("protocol_version", protocolVersion);
        if (action != null) json.addProperty("action", action);
        if (target != null) json.addProperty("target", target);
        if (source != null) json.addProperty("source", source);
        if (user != null) json.addProperty("user", user);
        json.addProperty("message", message);
        if (!success && errorCode != null) {
            json.addProperty("error", errorCode.getCode());
        }
        if (executionTimeMs >= 0) {
            json.addProperty("execution_time_ms", executionTimeMs);
        }
        if (messageId != null) json.addProperty("message_id", messageId);
        if (metadata != null) json.add("metadata", metadata);
        return json;
    }

    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }

    public String getAction() { return action; }
    public void setAction(String action) { this.action = action; }

    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }

    public ErrorCode getErrorCode() { return errorCode; }
    public void setErrorCode(ErrorCode errorCode) { this.errorCode = errorCode; }

    public String getTarget() { return target; }
    public void setTarget(String target) { this.target = target; }

    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }

    public String getUser() { return user; }
    public void setUser(String user) { this.user = user; }

    public String getMessageId() { return messageId; }
    public void setMessageId(String messageId) { this.messageId = messageId; }

    public long getExecutionTimeMs() { return executionTimeMs; }
    public void setExecutionTimeMs(long executionTimeMs) { this.executionTimeMs = executionTimeMs; }

    public int getProtocolVersion() { return protocolVersion; }
    public void setProtocolVersion(int protocolVersion) { this.protocolVersion = protocolVersion; }

    public JsonObject getMetadata() { return metadata; }
    public void setMetadata(JsonObject metadata) { this.metadata = metadata; }
}
