package com.thedeathlycow.novoatlas.world.gen.biome;

import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import it.unimi.dsi.fastutil.ints.IntArraySet;
import it.unimi.dsi.fastutil.ints.IntSet;
import net.minecraft.core.Holder;
import net.minecraft.world.level.biome.Biome;

import java.util.List;

public record BiomeColorEntry(
        Holder<Biome> biome,
        int color
) {
    public static final Codec<BiomeColorEntry> CODEC = RecordCodecBuilder.create(
            instance -> instance.group(
                    Biome.CODEC
                            .fieldOf("biome")
                            .forGetter(BiomeColorEntry::biome),
                    ColorHelper.CODEC
                            .fieldOf("color")
                            .forGetter(BiomeColorEntry::color)
            ).apply(instance, BiomeColorEntry::new)
    );

    public static final Codec<List<BiomeColorEntry>> LIST_CODEC = CODEC.listOf()
            .validate(BiomeColorEntry::validateList);

    private static DataResult<List<BiomeColorEntry>> validateList(List<BiomeColorEntry> entries) {
        if (entries.isEmpty()) {
            return DataResult.error(() -> "Biome color list may not be empty");
        }

        IntSet colors = new IntArraySet();
        for (BiomeColorEntry entry : entries) {
            if (colors.contains(entry.color)) {
                return DataResult.error(() -> String.format(
                        "Found duplicate color #%1$06x (%1$d) found for biome %2$s",
                        entry.color,
                        entry.biome
                ));
            }
            colors.add(entry.color);
        }

        return DataResult.success(entries);
    }
}
