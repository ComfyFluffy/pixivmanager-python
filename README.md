# PixivManager

A toolset for [Pixiv](https://www.pixiv.net/)

```bash
python -m pixivmanager
```

Welcome to submit feature requests & issues!

## Features

- Pixiv works downloader
- Ugoira to gif
- Local database with works and users' info (tags, captions, etc.)

## TODO

- [ ] Web UI for local Pixiv works lookup
- [ ] A Pixiv client in Web UI

## Usage

### CLI examples

Download all illust bookmarks of user 123456 which doesn't have tag "R-18G" and has tag "風景" or "R-18", with an API request times limit of 3 (last 90 works will be downloaded):

`pixivmanager bookmark --max 3 -user 123456 --type illust --tags-include 風景;R-18 --tags-exclude R-18G`

Download user 123456's ugoira:

`pixivmanager works -user 123456 --type ugoira`

Download login user's last 30 bookmarks:

`pixivmanager bookmark --max 1`
