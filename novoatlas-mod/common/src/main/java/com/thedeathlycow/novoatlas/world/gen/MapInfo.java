package com.thedeathlycow.novoatlas.world.gen;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import com.thedeathlycow.novoatlas.registry.ImageManager;
import com.thedeathlycow.novoatlas.registry.NovoAtlasResourceKeys;
import com.thedeathlycow.novoatlas.world.gen.biome.provider.ColorMapBiomeProvider;
import com.thedeathlycow.novoatlas.world.gen.biome.provider.LayeredMapBiomeProvider;
import net.minecraft.core.Holder;
import net.minecraft.resources.RegistryFileCodec;
import net.minecraft.resources.ResourceKey;
import net.minecraft.util.ExtraCodecs;
import net.minecraft.world.level.biome.Biome;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.Objects;
import java.util.Optional;

/**
 * 地图配置 — height_map 支持两种格式：
 * 1. "height_map": "namespace:key" （单张图，原有）
 * 2. "height_map": { "tile_size": ..., "tiles": "...", "width": ..., "height": ... } （瓦片，新增）
 */
public final class MapInfo {

    private final ImageSource heightMap;
    private final ColorMapBiomeProvider surfaceBiomes;
    private final Optional<LayeredMapBiomeProvider> caveBiomes;
    private final int startingY;
    private final int surfaceRange;
    private final float horizontalScale;
    private final float verticalScale;
    private final Optional<MapScaleConfig> scaling;

    /** 缓存的 MapImage（volatile + DCL） */
    private volatile MapImage cachedHeightMap;

    public static final Codec<MapInfo> DIRECT_CODEC = RecordCodecBuilder.create(
            instance -> instance.group(
                    ImageSource.codec(NovoAtlasResourceKeys.HEIGHTMAP)
                            .fieldOf("height_map")
                            .forGetter(MapInfo::heightMapSource),
                    ColorMapBiomeProvider.CODEC.codec()
                            .fieldOf("surface_biomes")
                            .forGetter(MapInfo::surfaceBiomes),
                    LayeredMapBiomeProvider.CODEC.codec()
                            .optionalFieldOf("cave_biomes")
                            .forGetter(MapInfo::caveBiomes),
                    Codec.INT
                            .fieldOf("starting_y")
                            .forGetter(MapInfo::startingY),
                    ExtraCodecs.POSITIVE_INT
                            .optionalFieldOf("surface_range", 16)
                            .forGetter(MapInfo::surfaceRange),
                    ExtraCodecs.POSITIVE_FLOAT
                            .optionalFieldOf("horizontal_scale", 1.0f)
                            .forGetter(MapInfo::horizontalScale),
                    ExtraCodecs.POSITIVE_FLOAT
                            .optionalFieldOf("vertical_scale", 1.0f)
                            .forGetter(MapInfo::verticalScale),
                    MapScaleConfig.CODEC
                            .optionalFieldOf("scaling")
                            .forGetter(MapInfo::scaling)
            ).apply(instance, MapInfo::new)
    );

    public static final Codec<Holder<MapInfo>> CODEC = RegistryFileCodec.create(
            NovoAtlasResourceKeys.MAP_INFO, DIRECT_CODEC
    );

    public MapInfo(
            ImageSource heightMap, ColorMapBiomeProvider surfaceBiomes,
            Optional<LayeredMapBiomeProvider> caveBiomes, int startingY,
            int surfaceRange, float horizontalScale, float verticalScale,
            Optional<MapScaleConfig> scaling
    ) {
        this.heightMap = heightMap;
        this.surfaceBiomes = surfaceBiomes;
        this.caveBiomes = caveBiomes;
        this.startingY = startingY;
        this.surfaceRange = surfaceRange;
        this.horizontalScale = horizontalScale;
        this.verticalScale = verticalScale;
        this.scaling = scaling;
    }

    // —— Getters ——
    public ImageSource heightMapSource() { return heightMap; }
    public ColorMapBiomeProvider surfaceBiomes() { return surfaceBiomes; }
    public Optional<LayeredMapBiomeProvider> caveBiomes() { return caveBiomes; }
    public int startingY() { return startingY; }
    public int surfaceRange() { return surfaceRange; }
    public Optional<MapScaleConfig> scaling() { return scaling; }

    /** 获取已解析的高度图 MapImage（延迟缓存） */
    public MapImage getHeightMap() {
        MapImage cached = this.cachedHeightMap;
        if (cached != null) return cached;
        synchronized (this) {
            cached = this.cachedHeightMap;
            if (cached != null) return cached;
            this.cachedHeightMap = this.heightMap.resolve(MapImage.Type.HEIGHTMAP, ImageManager.HEIGHTMAP);
            return this.cachedHeightMap;
        }
    }

    // —— Static helpers ——
    public static MapImage lookupHeightmap(ResourceKey<MapImage> map) {
        return Objects.requireNonNull(ImageManager.HEIGHTMAP.getImage(map), "Missing height map: " + map);
    }

    public static MapImage lookupBiomeMap(ResourceKey<MapImage> map) {
        return Objects.requireNonNull(ImageManager.BIOME_MAP.getImage(map), "Missing biome map: " + map);
    }

    // —— Sampling ——
    public int getHeightMapElevation(int x, int z, int fallback) {
        return getHeightMap().sample(x, z, this, fallback);
    }

    public int getHeightMapElevation(int x, int z) {
        return getHeightMap().sample(x, z, this);
    }

    @NotNull
    public Holder<Biome> getBiome(int x, int y, int z, @NotNull Holder<Biome> defaultBiome) {
        if (this.caveBiomes.isPresent()) {
            Holder<Biome> caveBiome = this.getCaveBiome(x, y, z, this.caveBiomes.orElseThrow());
            if (caveBiome != null) return caveBiome;
        }
        Holder<Biome> surfaceBiome = this.surfaceBiomes.getBiome(x, y, z, this);
        return surfaceBiome != null ? surfaceBiome : defaultBiome;
    }

    public float horizontalScale() {
        return this.scaling.map(MapScaleConfig::horizontalScale).orElse(this.horizontalScale);
    }

    public float verticalScale() {
        return this.scaling.map(MapScaleConfig::verticalScale).orElse(this.verticalScale);
    }

    @Nullable
    private Holder<Biome> getCaveBiome(int x, int y, int z, LayeredMapBiomeProvider caveBiomes) {
        int height = this.getHeightMapElevation(x, z, Integer.MIN_VALUE);
        if (height == Integer.MIN_VALUE) return null;
        if (y <= height - this.surfaceRange) {
            return caveBiomes.getBiome(x, y, z, this);
        }
        return null;
    }
}
