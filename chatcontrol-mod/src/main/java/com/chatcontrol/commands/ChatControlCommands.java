package com.chatcontrol.commands;

import com.chatcontrol.ChatControlMod;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.context.CommandContext;
import net.minecraft.server.command.CommandManager;
import net.minecraft.server.command.ServerCommandSource;
import net.minecraft.text.Text;

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
}
