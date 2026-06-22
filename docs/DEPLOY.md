# Deploy the website

The site is one static file: `docs/index.html`. No build step. Host the site free.

## Option A: GitHub Pages (simplest)

1. Push the repo to GitHub.
2. Open Settings, then Pages.
3. Set Source to "Deploy from a branch".
4. Pick branch `main` and folder `/docs`.
5. Save. Your site goes live at `https://<username>.github.io/replayx/`.

The `.nojekyll` file in `docs/` stops GitHub from running Jekyll, so the raw HTML serves as is.

## Option B: Cloudflare Pages, Netlify, or Vercel

1. Connect the GitHub repo.
2. Set the build command to none.
3. Set the output directory to `docs`.
4. Deploy. You get a free subdomain.

## Free domains, no cost

Free subdomains, instant, no payment:

- `<username>.github.io` from GitHub Pages
- `replayx.pages.dev` from Cloudflare Pages
- `replayx.netlify.app` from Netlify
- `replayx.vercel.app` from Vercel
- `replayx.readthedocs.io` from Read the Docs, good for Python docs
- `replayx.surge.sh` from Surge

Free real subdomains through community projects, signup or a pull request:

- `replayx.is-a.dev`, open a pull request to the is-a.dev repo
- `<name>.eu.org`, free registration with manual approval
- `replayx.js.org` accepts JavaScript projects only, so a Python library will not qualify

Note on Freenom: the free `.tk`, `.ml`, `.ga`, `.cf`, and `.gq` domains no longer work. Skip them.

## Point a custom domain at the site

1. Add a file named `CNAME` inside `docs/` with your domain on one line, for example `replayx.is-a.dev`.
2. In your DNS provider, add a CNAME record from your domain to `<username>.github.io`.
3. GitHub Pages issues HTTPS for the domain after DNS resolves.
