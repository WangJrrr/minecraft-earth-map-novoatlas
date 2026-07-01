package com.thedeathlycow.novoatlas.world.gen;

import net.minecraft.util.Mth;

import java.awt.image.BufferedImage;
import java.awt.image.Raster;

/**
 * 地图图像的抽象基类。
 * 子类实现 {@link #getPixel(int, int)} 提供逐像素访问。
 */
public abstract class MapImage {

    private final int width;
    private final int height;
    private final Type type;

    public enum Type { BIOME_MAP, HEIGHTMAP }

    protected MapImage(int width, int height, Type type) {
        this.width = width;
        this.height = height;
        this.type = type;
    }

    public int width() { return width; }
    public int height() { return height; }
    public Type type() { return type; }

    /** 子类必须实现的像素读取方法 */
    public abstract int getPixel(int x, int z);

    /** 从 BufferedImage 创建 SingleMapImage（小图整张加载） */
    public static MapImage fromBufferedImage(BufferedImage image, Type type) {
        return new SingleMapImage(image, type);
    }

    /** 从瓦片配置创建 TiledMapImage */
    public static MapImage fromTiledConfig(com.thedeathlycow.novoatlas.world.gen.tiled.TiledImageConfig config, Type type) {
        return new com.thedeathlycow.novoatlas.world.gen.tiled.TiledMapImage(config, type);
    }

    public int sample(int x, int z, MapInfo info) {
        return this.sample(x, z, info, Integer.MIN_VALUE);
    }

    public int sample(int x, int z, MapInfo info, int fallback) {
        double xR = (x / info.horizontalScale()) + this.width() / 2.0;
        double zR = (z / info.horizontalScale()) + this.height() / 2.0;

        if (xR < 0 || zR < 0 || xR >= this.width() || zR >= this.height()) {
            return fallback;
        }

        int truncatedX = Mth.floor(xR);
        int truncatedZ = Mth.floor(zR);

        if (this.type == Type.HEIGHTMAP) {
            double deltaX = xR - truncatedX;
            double deltaZ = zR - truncatedZ;
            double height = this.bilerp(truncatedX, deltaX, truncatedZ, deltaZ);
            return Mth.floor(info.verticalScale() * height + info.startingY());
        } else {
            return this.getPixel(truncatedX, truncatedZ);
        }
    }

    /** 双线性插值（硬编码，1.21.1 版本无独立插值器系统） */
    private double bilerp(int x, double deltaX, int z, double deltaZ) {
        int u0 = Math.max(0, x);
        int v0 = Math.max(0, z);
        int u1 = Math.min(width - 1, u0 + 1);
        int v1 = Math.min(v0 + 1, height - 1);

        double i00 = getPixel(u0, v0);
        double i01 = getPixel(u1, v0);
        double i10 = getPixel(u0, v1);
        double i11 = getPixel(u1, v1);

        return Mth.lerp2(Math.abs(deltaX), Math.abs(deltaZ), i00, i10, i01, i11);
    }
}
