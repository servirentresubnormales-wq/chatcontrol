package com.chatcontrol.commands;

import com.chatcontrol.ChatControlMod;
import com.chatcontrol.network.CommandReceiver;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.google.gson.JsonObject;
import net.minecraft.server.command.CommandManager;
import net.minecraft.server.command.ServerCommandSource;
import net.minecraft.text.Text;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

public class ChatControlCommands {

    public static void register(CommandDispatcher<ServerCommandSource> dispatcher) {
        dispatcher.register(CommandManager.literal("chatcontrol")
                .then(CommandManager.literal("start")
                        .requires(source -> source.hasPermissionLevel(2))
                        .executes(ChatControlCommands::start))
                .then(CommandManager.literal("stop")
                        .requires(source -> source.hasPermissionLevel(2))
                        .executes(ChatControlCommands::stop))
                .then(CommandManager.literal("status")
                        .executes(ChatControlCommands::status))
                .then(CommandManager.literal("reload")
                        .requires(source -> source.hasPermissionLevel(2))
                        .executes(ChatControlCommands::reload))
                .then(CommandManager.literal("reset")
                        .requires(source -> source.hasPermissionLevel(2))
                        .executes(ChatControlCommands::reset))
                .then(CommandManager.literal("link")
                        .requires(source -> source.hasPermissionLevel(0))
                        .then(CommandManager.argument("code", StringArgumentType.word())
                                .executes(ChatControlCommands::link)))
                .then(CommandManager.literal("unlink")
                        .requires(source -> source.hasPermissionLevel(0))
                        .executes(ChatControlCommands::unlink))
        );
    }

    private static int start(CommandContext<ServerCommandSource> context) {
        ChatControlMod.getSystemState().setEnabled(true);
        String message = "[ChatControl] System ACTIVATED by " + context.getSource().getName();
        ChatControlMod.LOGGER.info(message);
        context.getSource().sendFeedback(() -> Text.literal(message), true);
        return 1;
    }

    private static int stop(CommandContext<ServerCommandSource> context) {
        ChatControlMod.getSystemState().setEnabled(false);
        String message = "[ChatControl] System DEACTIVATED by " + context.getSource().getName();
        ChatControlMod.LOGGER.info(message);
        context.getSource().sendFeedback(() -> Text.literal(message), true);
        return 1;
    }

    private static int status(CommandContext<ServerCommandSource> context) {
        var state = ChatControlMod.getSystemState();
        var config = ChatControlMod.getConfig();

        StringBuilder sb = new StringBuilder();
        sb.append("=== ChatControl Status ===\n");
        sb.append("State: ").append(state.isEnabled() ? "ACTIVE" : "INACTIVE").append("\n");
        sb.append("Actions executed: ").append(state.getTotalActionsExecuted()).append("\n");
        sb.append("Uptime: ").append(state.getUptimeMs() / 1000).append("s\n");
        sb.append("Network: ").append(config.isNetworkEnabled() ? "ENABLED (port " + config.getNetworkPort() + ")" : "DISABLED").append("\n");
        sb.append("Auto-start: ").append(config.isAutoStart()).append("\n");
        sb.append("Max actions/min: ").append(config.getMaxActionsPerMinute()).append("\n");

        String status = sb.toString();
        context.getSource().sendFeedback(() -> Text.literal(status), false);
        return 1;
    }

    private static int reload(CommandContext<ServerCommandSource> context) {
        ChatControlMod.getConfig().reload();
        String message = "[ChatControl] Configuration reloaded.";
        ChatControlMod.LOGGER.info(message);
        context.getSource().sendFeedback(() -> Text.literal(message), true);
        return 1;
    }

    private static int reset(CommandContext<ServerCommandSource> context) {
        ChatControlMod.getSystemState().reset();
        ChatControlMod.getEventRegistry().clear();
        String message = "[ChatControl] System reset by " + context.getSource().getName();
        ChatControlMod.LOGGER.info(message);
        context.getSource().sendFeedback(() -> Text.literal(message), true);
        return 1;
    }

    private static int link(CommandContext<ServerCommandSource> context) {
        String code = StringArgumentType.getString(context, "code");

        if (!code.matches("\\d{6}")) {
            context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Link code must be exactly 6 digits."), false);
            return 0;
        }

        CommandReceiver receiver = ChatControlMod.getCommandReceiver();
        if (receiver == null) {
            context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Network receiver is not running."), false);
            return 0;
        }

        if (receiver.getConnectedClientCount() == 0) {
            context.getSource().sendFeedback(() -> Text.literal("[ChatControl] No Bridge is connected."), false);
            return 0;
        }

        String playerName = context.getSource().getName();
        CompletableFuture<JsonObject> future = receiver.broadcastLinkRequest(code, playerName);

        if (future == null) {
            context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Failed to send link request to Bridge."), false);
            return 0;
        }

        context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Link request sent, waiting for Bridge response..."), false);

        new Thread(() -> {
            try {
                JsonObject response = future.get(10, TimeUnit.SECONDS);
                boolean success = response.has("success") && response.get("success").getAsBoolean();
                String message = response.has("message") ? response.get("message").getAsString() : (success ? "Linked successfully" : "Link failed");
                String resultMsg = success ? "[ChatControl] " + message : "[ChatControl] Link failed: " + message;
                context.getSource().sendFeedback(() -> Text.literal(resultMsg), false);
            } catch (Exception e) {
                context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Link request timed out."), false);
            }
        }, "ChatControl-LinkWait").start();

        return 1;
    }

    private static int unlink(CommandContext<ServerCommandSource> context) {
        CommandReceiver receiver = ChatControlMod.getCommandReceiver();
        if (receiver == null) {
            context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Network receiver is not running."), false);
            return 0;
        }

        if (receiver.getConnectedClientCount() == 0) {
            context.getSource().sendFeedback(() -> Text.literal("[ChatControl] No Bridge is connected."), false);
            return 0;
        }

        String playerName = context.getSource().getName();
        CompletableFuture<JsonObject> future = receiver.broadcastUnlinkRequest(playerName);

        if (future == null) {
            context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Failed to send unlink request to Bridge."), false);
            return 0;
        }

        context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Unlink request sent, waiting for Bridge response..."), false);

        new Thread(() -> {
            try {
                JsonObject response = future.get(10, TimeUnit.SECONDS);
                boolean success = response.has("success") && response.get("success").getAsBoolean();
                String message = response.has("message") ? response.get("message").getAsString() : (success ? "Unlinked successfully" : "Unlink failed");
                String resultMsg = success ? "[ChatControl] " + message : "[ChatControl] Unlink failed: " + message;
                context.getSource().sendFeedback(() -> Text.literal(resultMsg), false);
            } catch (Exception e) {
                context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Unlink request timed out."), false);
            }
        }, "ChatControl-UnlinkWait").start();

        return 1;
    }
}
