package com.thedeathlycow.novoatlas.neoforge;

import com.thedeathlycow.novoatlas.NovoAtlas;
import com.thedeathlycow.novoatlas.registry.NovoAtlasResourceKeys;
import com.thedeathlycow.novoatlas.world.gen.HeightmapDensityFunction;
import com.thedeathlycow.novoatlas.world.gen.ImageMapChunkGenerator;
import com.thedeathlycow.novoatlas.world.gen.MapInfo;
import com.thedeathlycow.novoatlas.world.gen.biome.ColorMapBiomeSource;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.repository.Pack;
import net.minecraft.server.packs.repository.PackSource;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.AddPackFindersEvent;
import net.neoforged.neoforge.event.AddReloadListenerEvent;
import net.neoforged.neoforge.registries.DataPackRegistryEvent;
import net.neoforged.neoforge.registries.RegisterEvent;

@Mod(NovoAtlas.MOD_ID)
public final class NovoAtlasNeoForge {
    public NovoAtlasNeoForge(IEventBus bus) {
        NovoAtlas.init();

        NeoForge.EVENT_BUS.addListener(NovoAtlasNeoForge::registerResourceReloader);

        bus.addListener(NovoAtlasNeoForge::registerDatapackRegistries);
        bus.addListener(NovoAtlasNeoForge::register);
        bus.addListener(NovoAtlasNeoForge::addExamplePacks);
    }

    private static void addExamplePacks(AddPackFindersEvent event) {
        if (event.getPackType() == PackType.SERVER_DATA) {
            event.addPackFinders(
                    NovoAtlas.loc("resourcepacks/avila-basic-example"),
                    PackType.SERVER_DATA,
                    Component.literal("novoatlas/avila-basic-example"),
                    PackSource.FEATURE,
                    false,
                    Pack.Position.BOTTOM
            );

            event.addPackFinders(
                    NovoAtlas.loc("resourcepacks/avila-cave-biome-example"),
                    PackType.SERVER_DATA,
                    Component.literal("novoatlas/avila-cave-biome-example"),
                    PackSource.FEATURE,
                    false,
                    Pack.Position.BOTTOM
            );

            event.addPackFinders(
                    NovoAtlas.loc("resourcepacks/avila-no-caves-example"),
                    PackType.SERVER_DATA,
                    Component.literal("novoatlas/avila-no-caves-example"),
                    PackSource.FEATURE,
                    false,
                    Pack.Position.BOTTOM
            );
        }
    }

    private static void register(RegisterEvent event) {
        event.register(Registries.CHUNK_GENERATOR, NovoAtlas.loc("image_map"), () -> ImageMapChunkGenerator.CODEC);
        event.register(Registries.BIOME_SOURCE, NovoAtlas.loc("color_map"), () -> ColorMapBiomeSource.CODEC);
        event.register(Registries.DENSITY_FUNCTION_TYPE, NovoAtlas.loc("heightmap"), () -> HeightmapDensityFunction.DATA_CODEC);
    }

    private static void registerDatapackRegistries(DataPackRegistryEvent.NewRegistry event) {
        event.dataPackRegistry(NovoAtlasResourceKeys.MAP_INFO, MapInfo.DIRECT_CODEC);
    }

    private static void registerResourceReloader(AddReloadListenerEvent event) {
        event.addListener(new MapImageLoader());
    }
}
