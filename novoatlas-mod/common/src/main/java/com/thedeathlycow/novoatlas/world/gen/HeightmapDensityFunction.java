package com.thedeathlycow.novoatlas.world.gen;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.Holder;
import net.minecraft.util.KeyDispatchDataCodec;
import net.minecraft.util.Mth;
import net.minecraft.world.level.levelgen.DensityFunction;

/**
 * Computes a height density near the surface of the heightmap, but leaves negative density above and below the surface.
 * <p>
 * Essentially creates hollow mountains.
 *
 * @param mapInfo
 * @param transitionRange
 */
public record HeightmapDensityFunction(
        Holder<MapInfo> mapInfo,
        double transitionRange
) implements DensityFunction.SimpleFunction {
    public static final MapCodec<HeightmapDensityFunction> DATA_CODEC = RecordCodecBuilder.mapCodec(
            instance -> instance.group(
                    MapInfo.CODEC
                            .fieldOf("map_info")
                            .forGetter(HeightmapDensityFunction::mapInfo),
                    Codec.DOUBLE
                            .optionalFieldOf("transition_range", 10.0)
                            .forGetter(HeightmapDensityFunction::transitionRange)
            ).apply(instance, HeightmapDensityFunction::new)
    );

    public static final KeyDispatchDataCodec<HeightmapDensityFunction> CODEC = KeyDispatchDataCodec.of(DATA_CODEC);

    public HeightmapDensityFunction(Holder<MapInfo> mapInfo) {
        this(mapInfo, 10);
    }

    @Override
    public double compute(FunctionContext context) {
        int elevation = mapInfo.value().getHeightMapElevation(context.blockX(), context.blockZ(), Integer.MIN_VALUE);

        if (elevation == Integer.MIN_VALUE) {
            return -1.0;
        }

        int yOffset = elevation - context.blockY();

        return Mth.clampedMap(yOffset, -transitionRange, transitionRange, -1.0, 1.0);
    }

    @Override
    public double minValue() {
        return -1;
    }

    @Override
    public double maxValue() {
        return 1;
    }

    @Override
    public KeyDispatchDataCodec<? extends DensityFunction> codec() {
        return CODEC;
    }
}