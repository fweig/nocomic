# nocomic

Minimal manga reader that uses the browser to display images.

## Dependencies
```
pip3 install pillow
```

## Usage
```
python3 nocomic.py <PathToArchiveOrFolder>
```

Read at http://localhost:8080. Use `Ctrl+C` to exit.

Use arrow keys to navigate. Only supports right-to-left reading order at the moment.

Supported are `cbz`/`zip`-files and unpacked comic-archives (single folder containing only images).

Alternatively you may also open a folder containing any of the files above. In that case files are read in alphabetical order. Useful for reading series. Progress is saved.

## Upscaling

Also includes `upscale.py`, a small wrapper around waifu2x to easily upscale comic archives.

Installation:
 - Download [waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan) for your OS
 - Unpack archive to `nocomic/waifu2x-ncnn-vulkan`

Usage:
```
python3 upscale <Folder>
```
This command creates a folder `<Folder>_upscaled` with all comic archives passed through waifu2x.
