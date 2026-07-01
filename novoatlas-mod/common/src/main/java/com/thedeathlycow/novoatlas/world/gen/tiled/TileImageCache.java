package com.thedeathlycow.novoatlas.world.gen.tiled;

import com.thedeathlycow.novoatlas.NovoAtlas;

import java.awt.image.BufferedImage;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.BiFunction;

/**
 * 线程安全的 LRU 瓦片缓存。
 */
public final class TileImageCache {
    private static final int DEFAULT_MAX_TILES = 64;
    private final int maxTiles;
    private final BiFunction<Integer, Integer, BufferedImage> loader;
    private final LinkedHashMap<Long, BufferedImage> cache;
    private final ReentrantReadWriteLock lock = new ReentrantReadWriteLock();

    public TileImageCache(int maxTiles, BiFunction<Integer, Integer, BufferedImage> loader) {
        this.maxTiles = maxTiles;
        this.loader = loader;
        this.cache = new LinkedHashMap<>(maxTiles + 1, 0.75f, true) {
            protected boolean removeEldestEntry(Map.Entry<Long, BufferedImage> eldest) {
                return size() > TileImageCache.this.maxTiles;
            }
        };
    }

    public TileImageCache(BiFunction<Integer, Integer, BufferedImage> loader) {
        this(DEFAULT_MAX_TILES, loader);
    }

    public BufferedImage get(int tileX, int tileZ) {
        long key = packKey(tileX, tileZ);
        lock.readLock().lock();
        try {
            BufferedImage cached = cache.get(key);
            if (cached != null) return cached;
        } finally {
            lock.readLock().unlock();
        }
        lock.writeLock().lock();
        try {
            BufferedImage cached = cache.get(key);
            if (cached != null) return cached;
            NovoAtlas.LOGGER.debug("Loading tile ({}, {})", tileX, tileZ);
            BufferedImage loaded = loader.apply(tileX, tileZ);
            cache.put(key, loaded);
            return loaded;
        } finally {
            lock.writeLock().unlock();
        }
    }

    public int size() {
        lock.readLock().lock();
        try { return cache.size(); } finally { lock.readLock().unlock(); }
    }

    public void clear() {
        lock.writeLock().lock();
        try { cache.clear(); } finally { lock.writeLock().unlock(); }
    }

    private static long packKey(int tileX, int tileZ) {
        return ((long) tileX << 32) | (tileZ & 0xFFFFFFFFL);
    }
}
