# Release checklist

PageWisp is released to **GitHub Releases** only (desktop app, no app stores).
The version comes from the git tag; nothing in the code needs a manual version bump.

## Before tagging

- [ ] `uv run pytest` passes locally, and the latest **Build** run on `main` is green.
- [ ] Download the `PageWisp-windows` artifact from that `main` run, unzip it on a machine
      **without** Python, and check:
  - [ ] it starts, opens a real-world PDF and renders it sharply
  - [ ] scrolling, zoom (typed %, Ctrl+wheel, fit width/height), search and text selection work
  - [ ] a web link opens the browser; an internal link jumps and Alt+Left comes back
  - [ ] F1 shows the right version (`x.y.z-dev.N` for a main build)
- [ ] If the UI changed, retake `docs/screenshot.png`.
- [ ] Pick the version (semver): bug fixes → patch, new features → minor.
- [ ] Ask before pushing the tag: it publishes a public GitHub Release immediately.

## Release

```bash
git tag v1.2.3            # or v1.2.3-rc1 for a pre-release
git push origin v1.2.3
```

The **Build** workflow then runs the tests, builds and smoke-tests the app, and attaches
`PageWisp-1.2.3-windows.zip` to the release with auto-generated notes.

## After the release

- [ ] The release page has the zip, and the notes read sensibly (edit them if needed).
- [ ] Download the zip from the release page and launch it once more.
- [ ] If something is wrong, fix it on `main` and release a new patch version; don't move or
      reuse an existing tag.
