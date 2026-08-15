# justinmorg.github.io

Landing page and host for small one-off sites. Served by GitHub Pages from
`main` at root.

## Layout

```
index.html          landing page — the list of sites lives here
<site-name>/        one folder per site, each with its own index.html
```

A folder named `coin-log` publishes to `https://justinmorg.github.io/coin-log/`.

## Adding a site

1. Create the folder at the root with an `index.html` inside.
2. Use relative paths (`./style.css`, not `/style.css`) so the folder stays
   portable if it ever moves to its own repo.
3. Add a row to the list in `index.html` — the template is in a comment there.
4. Commit to `main`. Pages redeploys on push.

`.nojekyll` is present so files are served exactly as committed, with no
Jekyll build step.
