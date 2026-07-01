package com.thedeathlycow.novoatlas.world.gen;

import java.awt.image.BufferedImage;
import java.awt.image.Raster;

/**
 * 单张图片的 MapImage 实现 — int[][] 内存数组，O(1) 无锁访问。
 */
public final class SingleMapImage extends MapImage {
    private final int[][] pixels;

    SingleMapImage(BufferedImage image, Type type) {
        super(image.getWidth(), image.getHeight(), type);
        this.pixels = type == Type.BIOME_MAP
                ? getColorPixels(image, image.getWidth(), image.getHeight())
                : getGrayScalePixels(image, image.getWidth(), image.getHeight());
    }

    public int[][] pixels() { return pixels; }

    @Override
    public int getPixel(int x, int z) {
        if (x < 0 || z < 0 || x >= width() || z >= height()) return Integer.MIN_VALUE;
        return pixels[x][z];
    }

    private static int[][] getGrayScalePixels(BufferedImage image, int width, int height) {
        int[][] pixels = new int[width][height];
        Raster raster = image.getRaster();
        for (int x = 0; x < width; x++)
            for (int y = 0; y < height; y++)
                pixels[x][y] = raster.getSample(x, y, 0);
        return pixels;
    }

    private static int[][] getColorPixels(BufferedImage image, int width, int height) {
        int[] data = new int[width * height];
        image.getRGB(0, 0, width, height, data, 0, width);
        int[][] pixels = new int[width][height];
        int x = 0, y = 0;
        for (int datum : data) {
            if (x >= width) { x = 0; y++; }
            pixels[x++][y] = datum & 0xffffff;
        }
        return pixels;
    }
}
