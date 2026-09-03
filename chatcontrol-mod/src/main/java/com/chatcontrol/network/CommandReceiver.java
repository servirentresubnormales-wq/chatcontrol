package com.chatcontrol.network;

import com.chatcontrol.ChatControlMod;
import com.chatcontrol.actions.ActionExecutor;
import com.chatcontrol.actions.ActionParameters;
import com.chatcontrol.actions.ActionResult;
import com.chatcontrol.config.ModConfig;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;

import java.io.*;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

public class CommandReceiver {

    private static final Gson GSON = new GsonBuilder().create();

    private final ModConfig config;
    private final ActionExecutor actionExecutor;
    private final MinecraftServer server;
    private final AuthenticationManager authManager;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private ServerSocket serverSocket;
    private ExecutorService executorService;
    private int connectionCounter = 0;

    private static final int MAX_THREADS = 4;
    private static final int MAX_QUEUE_SIZE = 50;

    public CommandReceiver(ModConfig config, ActionExecutor actionExecutor, MinecraftServer server) {
        this.config = config;
        this.actionExecutor = actionExecutor;
        this.server = server;
        ModConfig.AuthenticationConfig authConfig = config.getAuthentication();
        this.authManager = new AuthenticationManager(
                authConfig.isEnabled(),
                authConfig.getToken(),
                authConfig.getTimeoutSeconds(),
                authConfig.getMaxFailedAttempts(),
                authConfig.getRateLimitWindowSeconds()
        );
    }

    AuthenticationManager getAuthManager() {
        return authManager;
    }

    public void start() {
        if (running.get()) {
            ChatControlMod.LOGGER.warn("[ChatControl] Network receiver is already running.");
            return;
        }

        running.set(true);
        executorService = new ThreadPoolExecutor(
                1, MAX_THREADS, 60L, TimeUnit.SECONDS,
                new LinkedBlockingQueue<>(MAX_QUEUE_SIZE),
                r -> {
                    Thread t = new Thread(r, "ChatControl-Network");
                    t.setDaemon(true);
                    return t;
                },
                (r, executor) -> ChatControlMod.LOGGER.warn("[ChatControl] Thread pool full, command rejected")
        );

        new Thread(this::run, "ChatControl-ServerSocket").start();
    }

    public void stop() {
        running.set(false);
        if (serverSocket != null && !serverSocket.isClosed()) {
            try {
                serverSocket.close();
            } catch (IOException e) {
                ChatControlMod.LOGGER.error("[ChatControl] Error closing server socket", e);
            }
        }
        if (executorService != null) {
            executorService.shutdownNow();
        }
    }

    private void run() {
        try {
            serverSocket = new ServerSocket(config.getNetworkPort());
            ChatControlMod.LOGGER.info("[ChatControl] Network receiver listening on port {}", config.getNetworkPort());

            while (running.get()) {
                try {
                    Socket clientSocket = serverSocket.accept();
                    executorService.submit(() -> handleClient(clientSocket));
                } catch (IOException e) {
                    if (running.get()) {
                        ChatControlMod.LOGGER.error("[ChatControl] Error accepting connection", e);
                    }
                }
            }
        } catch (IOException e) {
            if (running.get()) {
                ChatControlMod.LOGGER.error("[ChatControl] Failed to start network receiver on port {}: {}",
                        config.getNetworkPort(), e.getMessage());
            }
        }
    }

    private void handleClient(Socket clientSocket) {
        String connectionId;
        synchronized (this) {
            connectionId = "conn-" + (++connectionCounter);
        }

        if (authManager.isEnabled() && authManager.isRateLimited(connectionId)) {
            ChatControlMod.LOGGER.warn("[ChatControl] Rate limited connection from {}", clientSocket.getRemoteSocketAddress());
            try {
                clientSocket.close();
            } catch (IOException ignored) {}
            return;
        }

        try (BufferedReader in = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
             PrintWriter out = new PrintWriter(clientSocket.getOutputStream(), true)) {

            ChatControlMod.LOGGER.info("[ChatControl] Client connected: {} ({})", clientSocket.getRemoteSocketAddress(), connectionId);

            if (authManager.isEnabled()) {
                boolean authenticated = handleAuthentication(clientSocket, in, out, connectionId);
                if (!authenticated) {
                    return;
                }
            } else {
                authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.AUTHENTICATED);
            }

            String line;
            while (running.get() && (line = in.readLine()) != null) {
                if (authManager.getState(connectionId) != AuthenticationManager.ConnectionAuthState.AUTHENTICATED) {
                    out.println(GSON.toJson(BridgeResponse.error(ErrorCode.UNAUTHORIZED, "Not authenticated")));
                    continue;
                }
                if (line.length() > ProtocolConstants.MAX_MESSAGE_SIZE) {
                    out.println(GSON.toJson(BridgeResponse.error(ErrorCode.INVALID_JSON, "Message too large")));
                    continue;
                }
                String response = processCommand(line);
                out.println(response);
            }
        } catch (IOException e) {
            if (running.get()) {
                ChatControlMod.LOGGER.error("[ChatControl] Client connection error", e);
            }
        } finally {
            authManager.removeConnection(connectionId);
            try {
                clientSocket.close();
            } catch (IOException e) {
                // ignore
            }
            ChatControlMod.LOGGER.info("[ChatControl] Client disconnected: {}", connectionId);
        }
    }

    private boolean handleAuthentication(Socket clientSocket, BufferedReader in, PrintWriter out, String connectionId) {
        authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.AUTHENTICATING);

        try {
            clientSocket.setSoTimeout(authManager.getTimeoutSeconds() * 1000);
        } catch (Exception e) {
            // ignore if socket already closed
        }

        try {
            String authLine = in.readLine();
            if (authLine == null) {
                authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.REJECTED);
                return false;
            }

            JsonObject authJson;
            try {
                authJson = GSON.fromJson(authLine, JsonObject.class);
            } catch (Exception e) {
                out.println(GSON.toJson(createAuthResponse(false, "INVALID_JSON", "Invalid JSON")));
                authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.REJECTED);
                authManager.recordFailedAttempt(connectionId);
                return false;
            }

            if (authJson == null) {
                out.println(GSON.toJson(createAuthResponse(false, "INVALID_JSON", "Invalid JSON")));
                authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.REJECTED);
                authManager.recordFailedAttempt(connectionId);
                return false;
            }

            String type = authJson.has("type") ? authJson.get("type").getAsString() : "";
            if (!"auth".equals(type)) {
                out.println(GSON.toJson(createAuthResponse(false, "INVALID_PROTOCOL", "Expected auth message")));
                authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.REJECTED);
                authManager.recordFailedAttempt(connectionId);
                return false;
            }

            Integer protocolVersion = authJson.has("protocol_version") ? authJson.get("protocol_version").getAsInt() : null;
            if (protocolVersion == null || protocolVersion != ProtocolConstants.PROTOCOL_VERSION) {
                out.println(GSON.toJson(createAuthResponse(false, "INVALID_PROTOCOL", "Unsupported protocol version")));
                authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.REJECTED);
                authManager.recordFailedAttempt(connectionId);
                return false;
            }

            String token = authJson.has("token") ? authJson.get("token").getAsString() : "";
            if (!authManager.validateToken(token)) {
                out.println(GSON.toJson(createAuthResponse(false, "UNAUTHORIZED", "Invalid token")));
                authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.REJECTED);
                authManager.recordFailedAttempt(connectionId);
                ChatControlMod.LOGGER.warn("[ChatControl] Authentication failed for {}", connectionId);
                return false;
            }

            authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.AUTHENTICATED);
            authManager.clearFailedAttempts(connectionId);
            out.println(GSON.toJson(createAuthResponse(true, null, "Authenticated")));
            ChatControlMod.LOGGER.info("[ChatControl] Client authenticated: {}", connectionId);
            return true;

        } catch (IOException e) {
            authManager.setState(connectionId, AuthenticationManager.ConnectionAuthState.REJECTED);
            return false;
        }
    }

    private JsonObject createAuthResponse(boolean success, String error, String message) {
        JsonObject response = new JsonObject();
        response.addProperty("type", "auth");
        response.addProperty("success", success);
        response.addProperty("message", message);
        response.addProperty("protocol_version", ProtocolConstants.PROTOCOL_VERSION);
        if (error != null) {
            response.addProperty("error", error);
        }
        return response;
    }

    String processCommand(String jsonCommand) {
        long startTime = System.currentTimeMillis();

        JsonObject requestJson;
        try {
            requestJson = GSON.fromJson(jsonCommand, JsonObject.class);
            if (requestJson == null) {
                return GSON.toJson(BridgeResponse.error(ErrorCode.INVALID_JSON));
            }
        } catch (Exception e) {
            return GSON.toJson(BridgeResponse.error(ErrorCode.INVALID_JSON));
        }

        BridgeRequest request = BridgeRequest.fromJson(requestJson);

        if (request.getProtocolVersion() == null) {
            return GSON.toJson(BridgeResponse.error(ErrorCode.INVALID_PROTOCOL, "Missing protocol_version"));
        }
        if (!request.hasValidProtocolVersion()) {
            return GSON.toJson(BridgeResponse.error(ErrorCode.INVALID_PROTOCOL,
                    "Unsupported protocol version: " + request.getProtocolVersion()));
        }

        if (request.getAction() == null || request.getAction().isEmpty()) {
            return GSON.toJson(BridgeResponse.error(ErrorCode.MISSING_ACTION));
        }

        ActionParameters params = parseParams(request.getParams());

        final String action = request.getAction();
        final String targetName = request.getTarget();
        final String source = request.getSource();
        final String user = request.getUser();
        final String messageId = request.getMessageId();

        CompletableFuture<BridgeResponse> future = new CompletableFuture<>();
        server.execute(() -> {
            try {
                ServerPlayerEntity target = null;
                if (targetName != null) {
                    target = server.getPlayerManager().getPlayer(targetName);
                    if (target == null) {
                        future.complete(BridgeResponse.error(ErrorCode.PLAYER_NOT_FOUND,
                                "Player not found: " + targetName));
                        return;
                    }
                } else {
                    var playerList = server.getPlayerManager().getPlayerList();
                    if (playerList.isEmpty()) {
                        future.complete(BridgeResponse.error(ErrorCode.NO_PLAYERS_ONLINE));
                        return;
                    }
                    target = playerList.get(0);
                }

                long execStart = System.currentTimeMillis();
                ActionResult result = actionExecutor.execute(action, server, target, params);
                long execTime = System.currentTimeMillis() - execStart;

                BridgeResponse response;
                if (result.isSuccess()) {
                    response = BridgeResponse.success(action, targetName, execTime);
                } else {
                    ErrorCode code = result.getErrorCode() != null ? result.getErrorCode() : ErrorCode.EXECUTION_ERROR;
                    response = BridgeResponse.error(code, result.getMessage());
                }
                response.setSource(source);
                response.setUser(user);
                response.setMessageId(messageId);
                future.complete(response);
            } catch (Exception e) {
                future.complete(BridgeResponse.error(ErrorCode.EXECUTION_ERROR, "Error: " + e.getMessage()));
            }
        });

        try {
            BridgeResponse response = future.get(ProtocolConstants.DEFAULT_TIMEOUT_MS, TimeUnit.MILLISECONDS);
            response.setExecutionTimeMs(System.currentTimeMillis() - startTime);
            return GSON.toJson(response.toJson());
        } catch (TimeoutException e) {
            ChatControlMod.LOGGER.error("[ChatControl] Command timed out");
            return GSON.toJson(BridgeResponse.error(ErrorCode.COMMAND_TIMEOUT));
        } catch (Exception e) {
            ChatControlMod.LOGGER.error("[ChatControl] Error processing command: {}", e.getMessage());
            return GSON.toJson(BridgeResponse.error(ErrorCode.EXECUTION_ERROR, "Error: " + e.getMessage()));
        }
    }

    private ActionParameters parseParams(JsonObject paramsJson) {
        ActionParameters params = new ActionParameters();
        if (paramsJson == null) return params;

        for (String key : paramsJson.keySet()) {
            var element = paramsJson.get(key);
            if (element == null || element.isJsonNull()) {
                params.set(key, "");
            } else if (element.isJsonPrimitive()) {
                var primitive = element.getAsJsonPrimitive();
                if (primitive.isString()) {
                    params.set(key, primitive.getAsString());
                } else if (primitive.isNumber()) {
                    params.set(key, String.valueOf(primitive.getAsNumber()));
                } else if (primitive.isBoolean()) {
                    params.set(key, String.valueOf(primitive.getAsBoolean()));
                } else {
                    params.set(key, element.toString());
                }
            } else {
                params.set(key, element.toString());
            }
        }
        return params;
    }
}
