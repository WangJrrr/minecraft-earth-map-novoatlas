package com.thedeathlycow.novoatlas.mixin.compat.terrablender.present;

import com.thedeathlycow.novoatlas.world.gen.ImageMapChunkGenerator;
import com.thedeathlycow.novoatlas.world.gen.biome.ColorMapBiomeSource;
import net.minecraft.core.Holder;
import net.minecraft.core.RegistryAccess;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.dimension.LevelStem;
import net.minecraft.world.level.levelgen.NoiseGeneratorSettings;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import terrablender.api.RegionType;
import terrablender.api.SurfaceRuleManager;
import terrablender.util.LevelUtils;
import terrablender.worldgen.IExtendedNoiseGeneratorSettings;

@Mixin(LevelUtils.class)
public abstract class LevelUtilsMixin {

    @Inject(
            method = "initializeBiomes",
            at = @At("HEAD"),
            cancellable = true
    )
    private static void patchSurfaceRulesForColorMapBiomes(
            RegistryAccess registryAccess,
            Holder<DimensionType> dimensionType,
            ResourceKey<LevelStem> levelResourceKey,
            ChunkGenerator chunkGenerator,
            long seed,
            CallbackInfo ci
    ) {
        if (chunkGenerator instanceof ImageMapChunkGenerator imageMapChunkGenerator) {
            NoiseGeneratorSettings generatorSettings = imageMapChunkGenerator.generatorSettings().value();

            if (chunkGenerator.getBiomeSource() instanceof ColorMapBiomeSource) {
                RegionType regionType = LevelUtils.getRegionTypeForDimension(dimensionType);
                SurfaceRuleManager.RuleCategory ruleCategory = switch (regionType) {
                    case OVERWORLD -> SurfaceRuleManager.RuleCategory.OVERWORLD;
                    case NETHER -> SurfaceRuleManager.RuleCategory.NETHER;
                    case null -> null;
                };

                if (ruleCategory != null) {
                    IExtendedNoiseGeneratorSettings extendedNoiseGeneratorSettings = (IExtendedNoiseGeneratorSettings) (Object) generatorSettings;
                    extendedNoiseGeneratorSettings.setRuleCategory(ruleCategory);
                }
            }

            // crashes if this is in the same if block as the references to the terrablender classes, for some reason
            if (chunkGenerator.getBiomeSource() instanceof ColorMapBiomeSource) {
                ci.cancel();
            }
        }
    }
}