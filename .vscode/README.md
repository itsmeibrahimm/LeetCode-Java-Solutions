# `vscode` Developer Guide

[`extensions.json`](extensions.json) contains the recommended extensions for Visual Studio Code.

In [`settings.json.default`](settings.json.default), we have default editor settings (setting up format-on-save with `black` and also enabling various linting tools). Make a copy, and customize for your environment (ie. set a custom interpeter to your project's virtualenv)

```bash
cp settings.json.default settings.default
```
