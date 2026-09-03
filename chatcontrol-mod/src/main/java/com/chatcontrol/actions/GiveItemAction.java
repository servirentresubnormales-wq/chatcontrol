package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import net.minecraft.entity.ItemEntity;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.item.Items;
import net.minecraft.registry.Registries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.text.Text;
import net.minecraft.util.Identifier;

public class GiveItemAction implements ActionHandler {

    @Override
    public String getName() {
        return "give_item";
    }

    @Override
    public String getDescription() {
        return "Give items to the target player";
    }

    @Override
    public int getDefaultCooldownSeconds() {
        return 3;
    }

    @Override
    public boolean isDangerous() {
        return false;
    }

    @Override
    public boolean execute(MinecraftServer server, ServerPlayerEntity target, ActionParameters params) {
        if (target == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] give_item: No target player specified.");
            return false;
        }

        String itemId = params.get("item", "minecraft:stone");
        int count = params.getInt("count", 1);
        int maxItems = ChatControlMod.getConfig().getMaxItemsPerAction();

        if (count < 1 || count > maxItems) {
            count = Math.min(Math.max(count, 1), maxItems);
        }

        Identifier identifier = Identifier.tryParse(itemId);
        if (identifier == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] give_item: Invalid item ID: {}", itemId);
            return false;
        }

        Item item = Registries.ITEM.get(identifier);
        if (item == null || item == Items.AIR) {
            ChatControlMod.LOGGER.warn("[ChatControl] give_item: Unknown item: {}", itemId);
            return false;
        }

        ItemStack stack = new ItemStack(item, count);
        ItemEntity itemEntity = new ItemEntity(
                target.getWorld(),
                target.getX(),
                target.getY() + 1.5,
                target.getZ(),
                stack
        );
        target.getWorld().spawnEntity(itemEntity);

        target.sendMessage(Text.literal("§a[ChatControl] You received " + count + "x " + item.getName().getString()), false);
        ChatControlMod.LOGGER.info("[ChatControl] Gave {}x {} to {}", count, itemId, target.getName().getString());
        return true;
    }
}
