package com.chatcontrol.commands;

import com.chatcontrol.ChatControlMod;
import com.chatcontrol.events.EventRegistry;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.server.command.CommandManager;
import net.minecraft.server.command.ServerCommandSource;
import net.minecraft.text.Text;

public class EventCommands {

    public static void register(CommandDispatcher<ServerCommandSource> dispatcher, EventRegistry eventRegistry) {
        dispatcher.register(CommandManager.literal("evento")
                .then(CommandManager.literal("list")
                        .executes(EventCommands::listEvents))
                .then(CommandManager.literal("test")
                        .requires(source -> source.hasPermissionLevel(2))
                        .then(CommandManager.argument("event_name", StringArgumentType.word())
                                .executes(EventCommands::testEvent)))
        );
    }

    private static int listEvents(CommandContext<ServerCommandSource> context) {
        var events = ChatControlMod.getEventRegistry().getRegisteredEvents();
        if (events.isEmpty()) {
            context.getSource().sendFeedback(() -> Text.literal("[ChatControl] No events registered."), false);
        } else {
            StringBuilder sb = new StringBuilder("[ChatControl] Registered events:\n");
            events.forEach(def ->
                    sb.append("  - ").append(def.getName()).append(" (cooldown: ").append(def.getCooldownSeconds()).append("s)\n")
            );
            context.getSource().sendFeedback(() -> Text.literal(sb.toString()), false);
        }
        return 1;
    }

    private static int testEvent(CommandContext<ServerCommandSource> context) {
        String eventName = StringArgumentType.getString(context, "event_name");
        var event = ChatControlMod.getEventRegistry().getEvent(eventName);
        if (event == null) {
            context.getSource().sendError(Text.literal("[ChatControl] Unknown event: " + eventName));
            return 0;
        }

        var player = context.getSource().getPlayer();
        if (player == null) {
            context.getSource().sendError(Text.literal("[ChatControl] This command requires a player."));
            return 0;
        }

        boolean success = event.execute(
                context.getSource().getServer(),
                player,
                "console"
        );

        if (success) {
            context.getSource().sendFeedback(() -> Text.literal("[ChatControl] Event '" + eventName + "' executed successfully."), true);
        } else {
            context.getSource().sendError(Text.literal("[ChatControl] Failed to execute event: " + eventName));
        }
        return success ? 1 : 0;
    }
}
