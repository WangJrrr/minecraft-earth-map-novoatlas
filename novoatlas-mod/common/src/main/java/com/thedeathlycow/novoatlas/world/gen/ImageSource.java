package com.thedeathlycow.novoatlas.world.gen;

import com.mojang.datafixers.util.Either;
import com.mojang.serialization.Codec;
import com.thedeathlycow.novoatlas.registry.ImageManager;
import com.thedeathlycow.novoatlas.world.gen.tiled.TiledImageConfig;
import net.minecraft.core.Registry;
import net.minecraft.resources.ResourceKey;

import java.util.Objects;

/**
 * 地图图像来源 — 单张注册表图片 或 瓦片化配置。
 * Codec 先尝试解析 JSON 对象（TiledImageConfig），失败则解析字符串（ResourceKey）。
 */
public record ImageSource(Either<TiledImageConfig, ResourceKey<MapImage>> value) {

    public static Codec<ImageSource> codec(ResourceKey<Registry<MapImage>> registryKey) {
        return Codec.either(TiledImageConfig.CODEC, ResourceKey.codec(registryKey))
                .xmap(ImageSource::new, ImageSource::value);
    }

    public static ImageSource of(ResourceKey<MapImage> key) {
        return new ImageSource(Either.right(key));
    }

    public static ImageSource of(TiledImageConfig config) {
        return new ImageSource(Either.left(config));
    }

    public MapImage resolve(MapImage.Type type, ImageManager registry) {
        return value.map(
                config -> MapImage.fromTiledConfig(config, type),
                key -> Objects.requireNonNull(registry.getImage(key), "Missing map image: " + key)
        );
    }

    public boolean isTiled() { return value.left().isPresent(); }
}
