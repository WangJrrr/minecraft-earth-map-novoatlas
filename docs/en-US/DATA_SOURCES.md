# Data Sources and Attribution

[English](DATA_SOURCES.md) | [简体中文](../zh-CN/DATA_SOURCES_zh-CN.md)

The map-generation pipeline uses or references the following datasets:

- [ESA WorldCover 2021](https://esa-worldcover.org/en) — global land-cover classification.
- [WorldClim 2.1](https://www.worldclim.org/data/worldclim21.html) — global climate variables.
- [HydroRIVERS](https://www.hydrosheds.org/products/hydrorivers) — global river networks and hydrological attributes.
- [Natural Earth](https://www.naturalearthdata.com/) — lakes and auxiliary global vector layers.
- Global elevation tiles cached by the build pipeline.
- Mineral-deposit records curated by the project for the rich-ore layers.
- [USGS Mineral Resources Data System (MRDS)](https://www.usgs.gov/publications/mineral-resources-data-system-mrds) — mineral occurrences, commodities and historical deposit metadata.
- [Global Energy Monitor Global Coal Mine Tracker](https://www.gem.wiki/Global_Coal_Mine_Tracker) — supplemental anchors for major coal mines.

Raw datasets and build caches are not redistributed in this repository. Users who reproduce the pipeline must obtain the source datasets from their respective providers and comply with each provider's license, attribution, and redistribution terms.

MRDS is a historical resource inventory and does not necessarily reflect current mine status, ownership, production or reserves. The project's rich-ore rankings are gameplay-oriented transformations and must not be interpreted as current economic or geological assessments.
