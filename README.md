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
