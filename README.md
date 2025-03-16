# REFORGERATOR

**Date:** `16, March 2025`  
**Version:** `1.1.1`  
**License:** MIT License (See [LICENSE](LICENSE) file)  
**Author:** `Makkad`  

---

## 1.1. OVERVIEW

Reforgerator is an image processing tool designed for batch creation of framed icons with both Classic and Reforged graphic styles. It simplifies the process of generating complete icon sets simultaneously in multiple file formats.

---

## 1.2. FEATURES

- **Batch Image Processing** → Quickly generate complete icon sets tailored for both Classic and Reforged graphic styles.
- **File Format Support** → Export as:
  - `.dds` (DXT1, DXT3)
  - `.blp` (BLP1 JPEG)
  - `.tga`
  - `.png`
- **Image Modification** → Fixed cropping and black border addition to conceal previously generated frames.
- **Different Input Methods** → Select files manually, use drag-and-drop, or choose entire directories.
- **Command-Line Interface (CLI)** → Supports CLI mode for scripting and automation.
- **Multilanguage** → `English, Español, Русский, Tiếng Việt, 简体中文`.

---

## 1.3. INSTALLATION

1. Unpack the archive into a folder with read and write permissions for external programs.
2. Run the program from the extracted folder.

---

## 1.4. UNINSTALLATION

1. Run `uninstall.bat` to remove the application.

---

## 2. APPLICATION USAGE GUIDE

This application supports both Graphical User Interface (GUI) Mode and Command-Line Interface (CLI) Mode, allowing users to process images flexibly.

---

### 2.1. Running in GUI Mode

To launch the application in GUI mode, simply run the executable:

```bash
./Reforgerator
```

- A graphical interface will open, allowing users to add images, configure settings, and batch process tasks visually.
- No terminal or console output will be displayed.

---

### 2.2. Running in CLI Mode

To use the Command-Line Interface (CLI) mode, run the program with the `--cli` flag:

```bash
./Reforgerator --cli [options]
```

This mode allows advanced users to specify input files, directories, and configurations directly via the command line.

#### CLI Arguments

| Argument             | Description                                              |
| -------------------- | -------------------------------------------------------- |
| `--cli`, `--no-gui`  | Run the program in CLI mode instead of GUI.            |
| `-i`, `--image`      | Specify input images (e.g., `-i image1.png,image2.jpg`)   |
| `-d`, `--directory`  | Specify input directories containing images.           |
| `-c`, `--config`     | Use a custom configuration file to override defaults.    |

---

#### Console Output Behavior on Windows

On Windows, this application is recognized as a non-console application. Standard console output may not be visible unless explicitly redirected or handled. To deal with CLI output, use one of the following methods:

1. Using Windows `| more` command redirect the output through `more` to prevent text from disappearing:

    ```bash
    ./Reforgerator --cli --help | more
    ```

---

#### Examples (CLI)

**Basic Usage**

```bash
./Reforgerator --cli -i icon1.png
```

**Processing Images and Directories with Custom Config**

```bash
./Reforgerator --cli -i i1.png,i2.png -d f1/sf1,f2/sf2 -c profiles/profile_fullset.cfg
```

---

### 2.3. CUSTOMIZATION

#### Profiles

You can add custom profiles with specific settings by placing configuration files in the `profiles` directory using the following naming scheme:

```
profile_{custom_name}.cfg
```

Example:

```
profiles/profile_custom.cfg
```

#### Localization

To add language support, place localization files in the `localisations` directory using the following naming convention:

```
local_{lang}.txt
```

Example:

```
localisations/local_ge.txt
```

#### Custom Frames

Custom frames allow you to define personalized frame layouts via `.ini` configuration files. The program parses these files to automatically load and integrate your custom frames.

**How to configure custom frames:**

1. Create one or more `.ini` files in the `frames/custom_frames` directory. Each file should contain a main section and may include optional sections for specific sizes and styles.

2. In the main section, include the following required fields:
   - **id**: A unique identifier for the frame.
   - **name**: The display name for the frame.
   - **prefix**: Used for naming the input custom frame image and as the default prefix for output files.

   _Optional fields:_
   - **extension**: The frame image extension. If omitted, `.png` is used.
   - **main_folder**: The folder where frame assets are stored. If a relative path is given, the parent folder is set as `frames/custom_frames/main_folder`.

3. Additional sections specify detailed options for a given size and style. Each additional section should include:
   - **size**: The frame size (valid options: `size_64x64`, `size_128x128`, `size_256x256`).
   - **style**: The frame style (valid options: `style_hd`, `style_sd`).

   _Optional fields:_
   - **path**: The path to the frame image file. If omitted, a default path is used (e.g., `main_folder/256x256/Reforged/prefix.extension`).
   - **im_pos**: The image position as a tuple (x, y), representing the upper-left corner. Defaults to `(0,0)`.
   - **im_size**: The image size as a tuple (width, height). By default, it equals the frame size.

4. The parsing function reads all `.ini` files from the `custom_frames` directory and repairs missing or invalid fields when possible.

5. To update or add custom frames, simply add or modify your `.ini` file(s) in the `frames/custom_frames` directory and restart the application.

_Example SSH.ini file:_

```ini
[main]
id = custom_border_ssh
name = Scorescreen-Hero
prefix = SSH
main_folder = misc

[sd64]
size = size_64x64
style = style_sd
im_pos = 2,16
im_size = 32,32
path = SSH.png
```

Ensure your `.ini` files follow this structure so that custom frames are correctly parsed and integrated into the application.

---

## 3. MISCELLANEOUS

### 3.1. CHANGELOG

### 1.1.1 - 16, March 2025
- Minor optimization.

### 1.1.0 - 15, March 2025
- Added support for PSD input, including RGBA layers, opacity, and masks in regular blend mode.
- Introduced BLP1 JPEG handling with non-opaque alpha channels for both input and output.
- Implemented configurable input format filtering to process specific file types.
- Enabled multi-folder support for Drag-and-Drop and CLI inputs.
- Updated folder selection UI with a new icon.
- Added support for custom frames.
- Introduced new frame types: Scorescreen Hero (SSH) and Scorescreen Player (SSP).
- Added frame options for Disabled Passive (DISPAS) and Disabled Autocast (DISATC) icons.
- Expanded Drag-and-Drop functionality to cover the entire program window.
- Added simplified Chinese localization (`local_zh-CN.txt`).

### 1.0.0 - 08, March 2025
- Public release.

---

### 3.2. CREDITS

🎖 **Thanks to:**  
`RvzerBro (test), LeP (jpgwrapper), KoMaTo3 (py.texture.compress), mdboom (pytoshop)`

---

### 3.3. SUPPORT

🔹 **For issues, bugs, or feature requests, contact:**  
[https://discord.gg/6kJDWSAKFq](https://discord.gg/6kJDWSAKFq)

💙 **Support the author:**  
[ko-fi.com/makkad](ko-fi.com/makkad), [patreon.com/makkad](patreon.com/makkad), [boosty.to/makkad](boosty.to/makkad)

---

### 3.4. LICENSE

`Reforgerator` is licensed under the MIT License. For more details, see the [LICENSE](LICENSE) file.

---

© `2025`, `Makkad`