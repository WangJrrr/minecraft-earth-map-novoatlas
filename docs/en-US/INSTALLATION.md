# Installation and Server Deployment

[English](INSTALLATION.md) | [简体中文](../zh-CN/INSTALLATION_zh-CN.md)

## New Worlds

1. Install Minecraft 1.21.1 and NeoForge.
2. Install Create and its dependencies on both client and server.
3. Install the modified NovoAtlas JAR from this project's release on both sides.
4. Download exactly one Earth-map ZIP and extract it as a normal datapack folder.
5. Put that folder in the new world's `datapacks` directory before world creation.

The four packages represent two scales and two mutually exclusive ore models. Do not combine 1:200 with 1:400 or Original Rich Ore with Top100 Rich Ore.

## Existing Worlds

Datapacks affect newly generated chunks. Replacing a package does not rewrite existing terrain. Updating an already generated area requires deleting the affected chunks or starting a new world. Always back up a production server first.

## Chunky

Full-map pregeneration is not required. The world can generate while players explore. Chunky is useful for spawn regions, transport corridors, and planned activity areas, but generating the entire planet can consume substantial CPU time and disk space.

## Client and Server

NovoAtlas and Create should be installed on both client and server. The Earth-map datapack itself belongs in the server world's `datapacks` directory. In singleplayer, place it in the selected save.

