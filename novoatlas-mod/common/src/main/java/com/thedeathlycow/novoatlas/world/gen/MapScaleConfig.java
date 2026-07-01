package com.thedeathlycow.novoatlas.world.gen;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.util.ExtraCodecs;

public record MapScaleConfig(
        float horizontalScale,
        float verticalScale
) {
    public static final Codec<MapScaleConfig> CODEC = RecordCodecBuilder.create(
            instance -> instance.group(
                    ExtraCodecs.POSITIVE_FLOAT
                            .optionalFieldOf("horizontal_scale", 1.0f)
                            .forGetter(MapScaleConfig::horizontalScale),
                    ExtraCodecs.POSITIVE_FLOAT
                            .optionalFieldOf("vertical_scale", 1.0f)
                            .forGetter(MapScaleConfig::verticalScale)
            ).apply(instance, MapScaleConfig::new)
    );
}
