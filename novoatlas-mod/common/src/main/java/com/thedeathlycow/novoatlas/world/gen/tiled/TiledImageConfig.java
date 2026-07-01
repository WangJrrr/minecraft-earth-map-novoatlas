package com.thedeathlycow.novoatlas.world.gen.tiled;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.util.ExtraCodecs;

/**
 * 瓦片地图配置。
 * JSON 格式：
 * {
 *     "tile_size": 1024,
 *     "tiles": "namespace:path/{tx}_{tz}.png",
 *     "width": 81920,
 *     "height": 46080
 * }
 */
public record TiledImageConfig(
        int tileSize,
        String tilePattern,
        int worldWidth,
        int worldHeight
) {
    public static final Codec<TiledImageConfig> CODEC = RecordCodecBuilder.create(
            instance -> instance.group(
                    ExtraCodecs.POSITIVE_INT.fieldOf("tile_size").forGetter(TiledImageConfig::tileSize),
                    Codec.STRING.fieldOf("tiles").forGetter(TiledImageConfig::tilePattern),
                    ExtraCodecs.POSITIVE_INT.fieldOf("width").forGetter(TiledImageConfig::worldWidth),
                    ExtraCodecs.POSITIVE_INT.fieldOf("height").forGetter(TiledImageConfig::worldHeight)
            ).apply(instance, TiledImageConfig::new)
    );

    public String tilePath(int tileX, int tileZ) {
        return tilePattern
                .replace("{tx}", Integer.toString(tileX))
                .replace("{tz}", Integer.toString(tileZ));
    }
}
