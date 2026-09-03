package com.chatcontrol;

import com.chatcontrol.actions.ActionExecutor;
import com.chatcontrol.actions.ActionRegistry;
import com.chatcontrol.actions.GiveItemAction;
import com.chatcontrol.actions.SummonMobAction;
import com.chatcontrol.actions.ApplyEffectAction;
import com.chatcontrol.actions.ZombieAction;
import com.chatcontrol.actions.SpidersAction;
import com.chatcontrol.actions.SlownessAction;
import com.chatcontrol.actions.BlindnessAction;
import com.chatcontrol.actions.CreeperAction;
import com.chatcontrol.actions.StormAction;
import com.chatcontrol.actions.RandomTeleportAction;
import com.chatcontrol.actions.ExplosionAction;
import com.chatcontrol.actions.RandomEventAction;
import com.chatcontrol.actions.ChickensAction;
import com.chatcontrol.commands.ChatControlCommands;
import com.chatcontrol.commands.EventCommands;
import com.chatcontrol.config.ModConfig;
import com.chatcontrol.events.EventRegistry;
import com.chatcontrol.network.CommandReceiver;
import com.chatcontrol.state.SystemState;
import net.fabricmc.api.DedicatedServerModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.server.MinecraftServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ChatControlMod implements DedicatedServerModInitializer {

    public static final String MOD_ID = "chatcontrol";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    private static MinecraftServer server;
    private static SystemState systemState;
    private static ModConfig config;
    private static ActionExecutor actionExecutor;
    private static ActionRegistry actionRegistry;
    private static EventRegistry eventRegistry;
    private static CommandReceiver commandReceiver;

    @Override
    public void onInitializeServer() {
        LOGGER.info("[ChatControl] Initializing ChatControl mod...");

        config = ModConfig.load();
        LOGGER.info("[ChatControl] Configuration loaded.");

        systemState = new SystemState();
        actionRegistry = new ActionRegistry();
        actionExecutor = new ActionExecutor(actionRegistry);
        eventRegistry = new EventRegistry();

        registerActions();
        registerDefaultEvents();

        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            ChatControlCommands.register(dispatcher);
            EventCommands.register(dispatcher, eventRegistry);
        });
        LOGGER.info("[ChatControl] Commands registered.");

        ServerLifecycleEvents.SERVER_STARTED.register(this::onServerStarted);
        ServerLifecycleEvents.SERVER_STOPPING.register(this::onServerStopping);
        ServerTickEvents.END_SERVER_TICK.register(this::onServerTick);

        LOGGER.info("[ChatControl] Mod initialized successfully.");
    }

    private void onServerStarted(MinecraftServer server) {
        ChatControlMod.server = server;
        LOGGER.info("[ChatControl] Server started. System state: {}", systemState.isEnabled() ? "ENABLED" : "DISABLED");

        if (config.isAutoStart()) {
            systemState.setEnabled(true);
            LOGGER.info("[ChatControl] Auto-start enabled. System is now ACTIVE.");
        }

        if (config.isNetworkEnabled()) {
            commandReceiver = new CommandReceiver(config, actionExecutor, server);
            commandReceiver.start();
            LOGGER.info("[ChatControl] Network receiver started on port {}", config.getNetworkPort());
        }
    }

    private void onServerStopping(MinecraftServer server) {
        if (commandReceiver != null) {
            commandReceiver.stop();
            LOGGER.info("[ChatControl] Network receiver stopped.");
        }
        LOGGER.info("[ChatControl] Server stopping. Mod shut down.");
    }

    private void onServerTick(MinecraftServer server) {
        if (systemState.isEnabled()) {
            eventRegistry.tick(server);
        }
    }

    public static MinecraftServer getServer() {
        return server;
    }

    public static SystemState getSystemState() {
        return systemState;
    }

    public static ModConfig getConfig() {
        return config;
    }

    public static ActionExecutor getActionExecutor() {
        return actionExecutor;
    }

    public static ActionRegistry getActionRegistry() {
        return actionRegistry;
    }

    public static EventRegistry getEventRegistry() {
        return eventRegistry;
    }

    private void registerActions() {
        actionRegistry.register(new GiveItemAction());
        actionRegistry.register(new SummonMobAction());
        actionRegistry.register(new ApplyEffectAction());
        actionRegistry.register(new ZombieAction());
        actionRegistry.register(new SpidersAction());
        actionRegistry.register(new SlownessAction());
        actionRegistry.register(new BlindnessAction());
        actionRegistry.register(new CreeperAction());
        actionRegistry.register(new StormAction());
        actionRegistry.register(new RandomTeleportAction());
        actionRegistry.register(new ExplosionAction());
        actionRegistry.register(new RandomEventAction());
        actionRegistry.register(new ChickensAction());
        LOGGER.info("[ChatControl] {} actions registered: {}", actionRegistry.getRegisteredNames().size(), actionRegistry.getRegisteredNames());
    }

    private void registerDefaultEvents() {
        // Phase 1: No complex events registered yet
        // Events will be added in Phase 2
        LOGGER.info("[ChatControl] Default events registered.");
    }
}
