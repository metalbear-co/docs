# mirrord Documentation site

This repo contains the source for the [mirrord docs site](https://metalbear.com/mirrord/docs). It uses [GitBook](https://gitbook.com/) to generate documentation from markdown.

### Structure

The root of the GitBook docs is `./docs`, as defined in `.gitbook.yaml`. See [the GitBook docs](https://gitbook.com/docs/getting-started/git-sync/content-configuration) for more info.

### Development

**When you open a PR with changes**, GitBook will publish a preview and display the link under the `Checks` section at the bottom of the page that will show your changes - it does so via the [GitBook bot](https://github.com/gitbook-bot) installed in this repo.

Changes to **content and structure** are possible in the repo, and other changes must be made via the [GitBook platform](https://app.gitbook.com). To do so, you will need access to the MetalBear organisation.

When **changing the structure** of the docs, like creating a new page, you must update `./docs/SUMMARY.md` to reflect this. New folders should have a `README.md` as their overview page.