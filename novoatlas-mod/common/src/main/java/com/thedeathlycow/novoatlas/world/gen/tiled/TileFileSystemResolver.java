package com.thedeathlycow.novoatlas.world.gen.tiled;

import com.thedeathlycow.novoatlas.NovoAtlas;
import net.minecraft.resources.ResourceLocation;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Stream;

public final class TileFileSystemResolver {
    private static final ConcurrentHashMap<ResourceLocation, Optional<Path>> PATH_CACHE = new ConcurrentHashMap<>();

    private TileFileSystemResolver() {
    }

    public static Optional<BufferedImage> load(ResourceLocation id) {
        Optional<Path> path = PATH_CACHE.computeIfAbsent(id, TileFileSystemResolver::resolve);
        if (path.isEmpty()) {
            return Optional.empty();
        }

        try {
            BufferedImage image = ImageIO.read(path.orElseThrow().toFile());
            if (image == null) {
                throw new IOException("Unsupported image format");
            }
            return Optional.of(image);
        } catch (IOException e) {
            throw new RuntimeException("Failed to load tiled map image from filesystem: " + path.orElseThrow(), e);
        }
    }

    public static void clearCache() {
        PATH_CACHE.clear();
    }

    private static Optional<Path> resolve(ResourceLocation id) {
        Path relative = Path.of("data", id.getNamespace(), id.getPath());
        Path cwd = Path.of("").toAbsolutePath();

        Optional<Path> direct = findInPackRoot(cwd.resolve("datapacks"), relative);
        if (direct.isPresent()) return direct;

        Optional<Path> dedicatedWorld = findInPackRoot(cwd.resolve("world").resolve("datapacks"), relative);
        if (dedicatedWorld.isPresent()) return dedicatedWorld;

        Path saves = cwd.resolve("saves");
        if (!Files.isDirectory(saves)) return Optional.empty();

        try (Stream<Path> worlds = Files.list(saves)) {
            return worlds
                    .filter(Files::isDirectory)
                    .sorted(Comparator.comparingLong(TileFileSystemResolver::lastModified).reversed())
                    .map(world -> findInPackRoot(world.resolve("datapacks"), relative))
                    .filter(Optional::isPresent)
                    .map(Optional::orElseThrow)
                    .findFirst();
        } catch (IOException e) {
            NovoAtlas.LOGGER.warn("Failed to scan saves folder for tiled map image '{}'", id, e);
            return Optional.empty();
        }
    }

    private static Optional<Path> findInPackRoot(Path datapacks, Path relative) {
        if (!Files.isDirectory(datapacks)) return Optional.empty();

        try (Stream<Path> packs = Files.list(datapacks)) {
            return packs
                    .map(pack -> pack.resolve(relative))
                    .filter(Files::isRegularFile)
                    .findFirst();
        } catch (IOException e) {
            NovoAtlas.LOGGER.warn("Failed to scan datapack folder '{}'", datapacks, e);
            return Optional.empty();
        }
    }

    private static long lastModified(Path path) {
        try {
            return Files.getLastModifiedTime(path).toMillis();
        } catch (IOException e) {
            return 0L;
        }
    }
}
