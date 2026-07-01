package com.thedeathlycow.novoatlas.world.gen.biome.provider;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import com.thedeathlycow.novoatlas.registry.ImageManager;
import com.thedeathlycow.novoatlas.registry.NovoAtlasResourceKeys;
import com.thedeathlycow.novoatlas.world.gen.ImageSource;
import com.thedeathlycow.novoatlas.world.gen.MapImage;
import com.thedeathlycow.novoatlas.world.gen.MapInfo;
import com.thedeathlycow.novoatlas.world.gen.biome.BiomeColorEntry;
import it.unimi.dsi.fastutil.ints.Int2ObjectArrayMap;
import it.unimi.dsi.fastutil.ints.Int2ObjectMap;
import net.minecraft.core.Holder;
import net.minecraft.world.level.biome.Biome;
import org.jetbrains.annotations.Nullable;

import java.util.List;
import java.util.stream.Stream;

/**
 * 颜色图 → 生物群系映射。
 * map 字段支持单张图（字符串）和瓦片化（对象）两种格式。
 */
public final class ColorMapBiomeProvider implements BiomeMapProvider {
    public static final MapCodec<ColorMapBiomeProvider> CODEC = RecordCodecBuilder.mapCodec(
            instance -> instance.group(
                    ImageSource.codec(NovoAtlasResourceKeys.BIOME_MAP)
                            .fieldOf("map")
                            .forGetter(ColorMapBiomeProvider::getMap),
                    BiomeColorEntry.LIST_CODEC
                            .fieldOf("biomes")
                            .forGetter(ColorMapBiomeProvider::getBiomeColors),
                    Codec.BOOL
                            .optionalFieldOf("strict", false)
                            .forGetter(ColorMapBiomeProvider::isStrict)
            ).apply(instance, ColorMapBiomeProvider::new)
    );

    private final ImageSource map;
    private final List<BiomeColorEntry> biomeColors;
    private final boolean strict;
    private final Int2ObjectMap<Holder<Biome>> biomeToColorCache = new Int2ObjectArrayMap<>();

    /** 缓存的已解析 MapImage（volatile + DCL） */
    private volatile MapImage cachedImage;

    public ColorMapBiomeProvider(ImageSource map, List<BiomeColorEntry> biomeColors, boolean strict) {
        this.map = map;
        this.biomeColors = biomeColors;
        this.strict = strict;
        for (BiomeColorEntry entry : biomeColors)
            this.biomeToColorCache.put(entry.color(), entry.biome());
    }

    @Override @Nullable
    public Holder<Biome> getBiome(int x, int y, int z, MapInfo info) {
        MapImage image = getImage();
        int color = image.sample(x, z, info, Integer.MIN_VALUE);
        if (color == Integer.MIN_VALUE) return null;
        Holder<Biome> mapped = this.biomeToColorCache.get(color);
        if (mapped != null) return mapped;
        if (strict) return null;
        return getClosest(color);
    }

    private MapImage getImage() {
        MapImage cached = this.cachedImage;
        if (cached != null) return cached;
        synchronized (this) {
            cached = this.cachedImage;
            if (cached != null) return cached;
            this.cachedImage = this.map.resolve(MapImage.Type.BIOME_MAP, ImageManager.BIOME_MAP);
            return this.cachedImage;
        }
    }

    @Override public Stream<Holder<Biome>> collectPossibleBiomes() {
        return this.biomeColors.stream().map(BiomeColorEntry::biome);
    }
    @Override public MapCodec<ColorMapBiomeProvider> getCodec() { return CODEC; }

    public ImageSource getMap() { return map; }
    public List<BiomeColorEntry> getBiomeColors() { return biomeColors; }
    public boolean isStrict() { return strict; }

    @Nullable
    private Holder<Biome> getClosest(int color) {
        double closestDistance = Integer.MAX_VALUE;
        int closest = -1;
        int red = red(color), green = green(color), blue = blue(color);
        for (int candidate : this.biomeToColorCache.keySet()) {
            int dRed = red(candidate) - red, dGreen = green(candidate) - green, dBlue = blue(candidate) - blue;
            double dist = dRed * dRed + dGreen * dGreen + dBlue * dBlue;
            if (dist < closestDistance) { closestDistance = dist; closest = candidate; }
        }
        return this.biomeToColorCache.getOrDefault(closest, null);
    }
    private static int red(int c) { return c & 0xFF0000 >> 16; }
    private static int green(int c) { return c & 0xFF00 >> 8; }
    private static int blue(int c) { return c & 0xFF; }
}
