package com.chatcontrol.actions;

import com.chatcontrol.ChatControlMod;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityType;
import net.minecraft.registry.Registries;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.ChunkPos;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.World;

import java.util.Random;

public class SpawnUtils {

    private static final Random RANDOM = new Random();
    private static final ChunkPositionHelper CHUNK_HELPER = new ChunkPositionHelper(RANDOM);

    public static ServerWorld getPlayerWorld(ServerPlayerEntity player) {
        return player.getServerWorld();
    }

    public static ChunkPos getPlayerChunk(ServerPlayerEntity player) {
        return player.getChunkPos();
    }

    public static int getChunkStartX(ServerPlayerEntity player) {
        ChunkPos chunk = getPlayerChunk(player);
        return CHUNK_HELPER.getChunkStartBlockX(chunk.x);
    }

    public static int getChunkStartZ(ServerPlayerEntity player) {
        ChunkPos chunk = getPlayerChunk(player);
        return CHUNK_HELPER.getChunkStartBlockZ(chunk.z);
    }

    public static int getChunkEndX(ServerPlayerEntity player) {
        ChunkPos chunk = getPlayerChunk(player);
        return CHUNK_HELPER.getChunkEndBlockX(chunk.x);
    }

    public static int getChunkEndZ(ServerPlayerEntity player) {
        ChunkPos chunk = getPlayerChunk(player);
        return CHUNK_HELPER.getChunkEndBlockZ(chunk.z);
    }

    public static Vec3d getRandomPositionInPlayerChunk(ServerPlayerEntity player, SpawnConfig config) {
        ChunkPos chunk = getPlayerChunk(player);
        int playerX = (int) player.getX();
        int playerZ = (int) player.getZ();

        int encoded = CHUNK_HELPER.findRandomPositionInChunk(
                chunk.x, chunk.z, playerX, playerZ, config);

        int x = ChunkPositionHelper.decodeX(encoded);
        int z = ChunkPositionHelper.decodeZ(encoded);

        return new Vec3d(x, player.getY(), z);
    }

    public static boolean spawnEntityInChunk(EntityType<?> type, ServerPlayerEntity player, SpawnConfig config) {
        ServerWorld world = getPlayerWorld(player);
        Vec3d pos = getRandomPositionInPlayerChunk(player, config);

        Entity entity = type.create(world);
        if (entity == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] Failed to create entity of type {}",
                    Registries.ENTITY_TYPE.getId(type));
            return false;
        }

        BlockPos blockPos = findSafeSpawnPos(world, (int) pos.x, (int) pos.y, (int) pos.z);
        if (blockPos == null) {
            blockPos = findSafeSpawnPosFallback(world, (int) pos.x, (int) pos.y, (int) pos.z);
        }
        if (blockPos == null) {
            ChatControlMod.LOGGER.warn("[ChatControl] Could not find valid spawn position in chunk");
            return false;
        }

        entity.setPosition(blockPos.getX() + 0.5, blockPos.getY(), blockPos.getZ() + 0.5);
        world.spawnEntity(entity);
        return true;
    }

    public static boolean spawnMultipleEntitiesInChunk(EntityType<?> type, ServerPlayerEntity player,
                                                        int count, SpawnConfig config) {
        ServerWorld world = getPlayerWorld(player);
        int spawned = 0;

        for (int i = 0; i < count; i++) {
            Vec3d pos = getRandomPositionInPlayerChunk(player, config);
            Entity entity = type.create(world);
            if (entity == null) continue;

            BlockPos blockPos = findSafeSpawnPos(world, (int) pos.x, (int) pos.y, (int) pos.z);
            if (blockPos == null) {
                blockPos = findSafeSpawnPosFallback(world, (int) pos.x, (int) pos.y, (int) pos.z);
            }
            if (blockPos == null) continue;

            entity.setPosition(blockPos.getX() + 0.5, blockPos.getY(), blockPos.getZ() + 0.5);
            world.spawnEntity(entity);
            spawned++;
        }

        return spawned > 0;
    }

    public static BlockPos findSafeSpawnPos(ServerWorld world, int x, int y, int z) {
        for (int attempt = 0; attempt < 10; attempt++) {
            int testY = y + RANDOM.nextInt(5) - 2;
            testY = CHUNK_HELPER.clampY(testY);
            BlockPos pos = new BlockPos(x, testY, z);

            if (isSafeForEntity(world, pos)) {
                return pos;
            }
        }
        return null;
    }

    public static BlockPos findSafeSpawnPosFallback(ServerWorld world, int x, int y, int z) {
        int minY = Math.max(y - 10, world.getBottomY());
        int maxY = Math.min(y + 10, world.getTopY());

        for (int dy = -10; dy <= 10; dy++) {
            int testY = y + dy;
            if (testY < minY || testY > maxY) continue;

            BlockPos pos = new BlockPos(x, testY, z);
            if (isSafeForEntity(world, pos)) {
                return pos;
            }
        }
        return null;
    }

    public static boolean isSafeForEntity(ServerWorld world, BlockPos pos) {
        boolean posAir = world.getBlockState(pos).isAir();
        boolean aboveAir = world.getBlockState(pos.up()).isAir();
        boolean belowSolid = !world.getBlockState(pos.down()).isAir();
        boolean notLava = !world.getBlockState(pos).getFluidState().isStill();

        return posAir && aboveAir && belowSolid && notLava;
    }

    public static boolean isSafeForTeleport(ServerWorld world, BlockPos pos) {
        boolean posAir = world.getBlockState(pos).isAir();
        boolean aboveAir = world.getBlockState(pos.up()).isAir();
        boolean belowSolid = !world.getBlockState(pos.down()).isAir();
        boolean notLava = !world.getBlockState(pos).getFluidState().isStill();
        boolean notVoid = pos.getY() > world.getBottomY();

        return posAir && aboveAir && belowSolid && notLava && notVoid;
    }

    public static boolean createExplosionInChunk(ServerPlayerEntity player, float radius,
                                                  boolean fire, World.ExplosionSourceType sourceType,
                                                  SpawnConfig config) {
        Vec3d pos = getRandomPositionInPlayerChunk(player, config);
        World world = player.getWorld();

        world.createExplosion(
                player,
                pos.x,
                player.getY() + 0.5,
                pos.z,
                radius,
                fire,
                sourceType
        );
        return true;
    }

    public static boolean teleportToChunkPosition(ServerPlayerEntity player, SpawnConfig config) {
        ServerWorld world = getPlayerWorld(player);
        ChunkPos chunk = getPlayerChunk(player);
        int playerX = (int) player.getX();
        int playerZ = (int) player.getZ();

        for (int attempt = 0; attempt < config.getMaxAttempts(); attempt++) {
            int encoded = CHUNK_HELPER.findRandomPositionInChunk(
                    chunk.x, chunk.z, playerX, playerZ, config);

            int x = ChunkPositionHelper.decodeX(encoded);
            int z = ChunkPositionHelper.decodeZ(encoded);

            for (int dy = 10; dy >= -10; dy--) {
                int testY = CHUNK_HELPER.clampY((int) player.getY() + dy);
                BlockPos pos = new BlockPos(x, testY, z);

                if (isSafeForTeleport(world, pos)) {
                    player.teleport(world, pos.getX() + 0.5, pos.getY(), pos.getZ() + 0.5,
                            player.getYaw(), player.getPitch());
                    return true;
                }
            }
        }

        return false;
    }

    public static ChunkPositionHelper getChunkHelper() {
        return CHUNK_HELPER;
    }
}
