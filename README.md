# Dark Sector Tools

A collection of tools for modding Dark Sector.

## Font Tool

The game's font textures are stored as `.tga.1` files inside `.cache` archives. These files contain raw DXT3 (BC2) compressed texture data without headers.

### How It Works

- **Extract**: Converts `.tga.1` font texture files to editable `.png` images (white glyphs on black background).
- **Repack**: Converts edited `.png` images back to `.tga.1` format, preserving the original DXT3 encoding.

### Usage

1. Extract the `.cache` archive using the **Cache** tab to get `.tga.1` files.
2. Switch to the **Font** tab, select a `.tga.1` file (or a folder for batch processing), and extract to PNG.
3. Edit the PNG in any image editor. Keep the format: white characters on a black background.
4. Repack the edited PNG back to `.tga.1` by providing the edited PNG, the original `.tga.1` (for format/size reference), and an output path.
5. Repack the `.cache` archive with the modified `.tga.1` files using the **Cache** tab.

### Font Files

The following font texture files are found inside the game's `.cache` archives:

| File | Type | Resolution | Description |
|------|------|-----------|-------------|
| `MenuFontGlyph_en_font.tga.1` | Glyph | 2048×1024 | Main menu font |
| `MenuFontShadow_en_font.tga.1` | Shadow | 2048×2048 | Main menu font shadow |
| `MenuTitleFontGlyph_en_font.tga.1` | Glyph | 1024×1024 | Menu title font |
| `MenuTitleFontShadow_en_font.tga.1` | Shadow | 1024×1024 | Menu title font shadow |
| `MenuTitleSmallFontGlyph_en_font.tga.1` | Glyph | 2048×1024 | Small menu title font |
| `MenuTitleSmallFontShadow_en_font.tga.1` | Shadow | 2048×1024 | Small menu title font shadow |
| `SubtitlesFontGlyph_en_font.tga.1` | Glyph | 1024×1024 | Subtitles font |
| `SubtitlesFontShadow_en_font.tga.1` | Shadow | 1024×1024 | Subtitles font shadow |
| `CommentFontGlyph_en_font.tga.1` | Glyph | 1024×1024 | In-game comment font |
| `DebugFontGlyph_en_font.tga.1` | Glyph | 512×512 | Debug font |
| `DarkitectIconLabelGlyph_en_font.tga.1` | Glyph | 2048×1024 | Darkitect icon label font |
| `PreviewFontGlyph_en_font.tga.1` | Glyph | 512×512 | Preview/editor font |

> **Language tags**: The `_en_` part in filenames indicates the language (English). Different language versions use different tags, for example `_it_` for Italian, `_de_` for German, etc.

### Font File Types

| Type | Description |
|------|-------------|
| `*Glyph*.tga.1` | Main font glyphs. Sharp, solid characters. |
| `*Shadow*.tga.1` | Drop shadow/glow textures. Softer appearance is intentional (DXT3 4-bit alpha). |

### Supported Sizes

All detected automatically from file size:

| File Size | Resolution |
|-----------|-----------|
| 4 MB | 2048×2048 |
| 2 MB | 2048×1024 |
| 1 MB | 1024×1024 |
| 512 KB | 1024×512 |
| 256 KB | 512×512 |

## Cache Tool

The game stores its assets in ZIP-based `.cache` archives that use a custom compression method (method 64), a chunked LZFX variant specific to Dark Sector. Standard ZIP tools can't handle this format.

### Usage

- **Extract**: Select a `.cache` file and an output directory to extract all files.
- **Repack**: Provide the original `.cache` (for structure reference), a folder with modified files, and an output path. Unmodified files are copied from the original archive. Modified files are stored uncompressed (method 0).

## Text Tool

The `Text Tool` folder contains two pre-compiled executables for working with the game's text/localization file (`Languages.cl.1`):

- **darksector_export_xbox-ps3.exe** — Extracts `Languages.cl.1` to an editable text file.
- **darksector_import_xbox-ps3.exe** — Converts the edited text file back to `Languages.cl.1` format.

> **Note**: The source code and original author of these text tools are unknown. They are included as-is for convenience. They are not part of this project's codebase.

## Platform Compatibility

| Tool | PS3 | Xbox 360 | PC |
|------|-----|----------|-----|
| Font Tool | ✅ Tested | 🟡 Should work, not tested | ❓ Unknown |
| Cache Tool | ✅ Tested | 🟡 Should work, not tested | ❓ Unknown |
| Text Tool | ✅ Tested | ✅ Tested | 🟡 Should work, not tested |

## Notes

- Some files appear multiple times in the archive with different versions. The tool handles these correctly during repack.
- The game doesn't use the CRC32 field in its ZIP headers, it's always zero. The tool preserves this.
- No external dependencies are required to run the `.exe` release. The Python source requires `Pillow` (`pip install Pillow`).
