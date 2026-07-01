package com.thedeathlycow.novoatlas.world.gen.biome;

import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import com.thedeathlycow.novoatlas.world.gen.biome.provider.ColorMapBiomeProvider;

import java.util.Optional;
import java.util.function.IntPredicate;

public record BiomeLayerEntry(
        Range yRange,
        ColorMapBiomeProvider biomeProvider
) {
    public static final Codec<BiomeLayerEntry> CODEC = RecordCodecBuilder.create(
            instance -> instance.group(
                    Range.CODEC
                            .fieldOf("y_range")
                            .forGetter(BiomeLayerEntry::yRange),
                    ColorMapBiomeProvider.CODEC.codec()
                            .fieldOf("biomes")
                            .forGetter(BiomeLayerEntry::biomeProvider)
            ).apply(instance, BiomeLayerEntry::new)
    );

    public boolean isInLayer(int y) {
        return yRange.test(y);
    }

    private record Range(Optional<Integer> min, Optional<Integer> max) implements IntPredicate {
        public static final Codec<Range> CODEC = RecordCodecBuilder.<Range>create(
                instance -> instance.group(
                        Codec.INT
                                .optionalFieldOf("min")
                                .forGetter(Range::min),
                        Codec.INT
                                .optionalFieldOf("max")
                                .forGetter(Range::max)
                ).apply(instance, Range::new)
        ).validate(range -> {
            int minValue = range.min.orElse(Integer.MIN_VALUE);
            int maxValue = range.max.orElse(Integer.MAX_VALUE);

            if (minValue >= maxValue) {
                return DataResult.error(() -> "Min is not less than max in: " + range, range);
            } else {
                return DataResult.success(range);
            }
        });

        @Override
        public boolean test(int y) {
            int minValue = this.min.orElse(Integer.MIN_VALUE);
            int maxValue = this.max.orElse(Integer.MAX_VALUE);

            return minValue <= y && y <= maxValue;
        }
    }
}