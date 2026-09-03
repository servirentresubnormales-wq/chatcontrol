package com.chatcontrol.network;

import com.google.gson.JsonObject;

public class BridgeRequest {

    private String action;
    private String target;
    private String source;
    private String user;
    private JsonObject params;
    private String messageId;
    private Integer protocolVersion;
    private String authToken;
    private JsonObject metadata;

    public BridgeRequest() {}

    public BridgeRequest(String action, String target) {
        this.action = action;
        this.target = target;
    }

    public String getAction() { return action; }
    public void setAction(String action) { this.action = action; }

    public String getTarget() { return target; }
    public void setTarget(String target) { this.target = target; }

    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }

    public String getUser() { return user; }
    public void setUser(String user) { this.user = user; }

    public JsonObject getParams() { return params; }
    public void setParams(JsonObject params) { this.params = params; }

    public String getMessageId() { return messageId; }
    public void setMessageId(String messageId) { this.messageId = messageId; }

    public Integer getProtocolVersion() { return protocolVersion; }
    public void setProtocolVersion(Integer protocolVersion) { this.protocolVersion = protocolVersion; }

    public String getAuthToken() { return authToken; }
    public void setAuthToken(String authToken) { this.authToken = authToken; }

    public JsonObject getMetadata() { return metadata; }
    public void setMetadata(JsonObject metadata) { this.metadata = metadata; }

    public static BridgeRequest fromJson(JsonObject json) {
        BridgeRequest request = new BridgeRequest();
        if (json.has("action")) request.setAction(json.get("action").getAsString());
        if (json.has("target")) request.setTarget(json.get("target").getAsString());
        else if (json.has("player")) request.setTarget(json.get("player").getAsString());
        if (json.has("source")) request.setSource(json.get("source").getAsString());
        if (json.has("user")) request.setUser(json.get("user").getAsString());
        if (json.has("params") && json.get("params").isJsonObject()) {
            request.setParams(json.getAsJsonObject("params"));
        }
        if (json.has("message_id")) request.setMessageId(json.get("message_id").getAsString());
        if (json.has("protocol_version")) request.setProtocolVersion(json.get("protocol_version").getAsInt());
        if (json.has("auth_token")) request.setAuthToken(json.get("auth_token").getAsString());
        if (json.has("metadata") && json.get("metadata").isJsonObject()) {
            request.setMetadata(json.getAsJsonObject("metadata"));
        }
        return request;
    }

    public JsonObject toJson() {
        JsonObject json = new JsonObject();
        json.addProperty("action", action);
        if (target != null) json.addProperty("target", target);
        if (source != null) json.addProperty("source", source);
        if (user != null) json.addProperty("user", user);
        if (params != null) json.add("params", params);
        if (messageId != null) json.addProperty("message_id", messageId);
        json.addProperty("protocol_version", ProtocolConstants.PROTOCOL_VERSION);
        if (authToken != null) json.addProperty("auth_token", authToken);
        if (metadata != null) json.add("metadata", metadata);
        return json;
    }

    public boolean hasValidProtocolVersion() {
        return protocolVersion != null && protocolVersion == ProtocolConstants.PROTOCOL_VERSION;
    }
}
