# Public release and GitHub Pages

Nothing is published by local builds. These steps apply to the standalone
`nashvel/codex-island` GitHub repository.

## Before making the repository public

1. Review the source, screenshots, brand assets, license, Git history and staged
   diff. Exclude credentials, private transcripts and generated artifacts.
2. Confirm you have the rights to distribute the supplied branding under MIT.
3. Enable Actions and private vulnerability reporting. Protect `main` with review
   requirements and the CI checks once their first run has completed.
4. Run the commands in CONTRIBUTING.md, including desktop acceptance.
5. Confirm the desktop launcher works after installing from the new layout.

The license covers this project's source and included assets. Codex CLI, GTK,
VTE and other external dependencies are not bundled and retain their licenses.

## Workflows

| Workflow | Trigger | Result |
| --- | --- | --- |
| CI | Main pushes, pull requests, manual runs and reusable calls | Python 3.10/3.14 headless checks; Linux native UI tests; site validation |
| Draft source release | Push a `v*` tag | Re-runs CI, verifies VERSION, packages source and SHA256, creates a draft release |
| Deploy showcase | Manual run on `main` only | Builds and deploys the static showcase to GitHub Pages |

CI has read-only repository access. Only the release job can write release data.
Only the Pages deployment job receives Pages and OIDC write permissions. Pull
requests do not receive publishing permissions. Third-party action versions are
maintained through monthly Dependabot pull requests.

Actions require a GitHub push to run; local checks do not prove a hosted workflow
has passed. Native UI tests use Ubuntu 24.04, Xvfb, Openbox and a private D-Bus
session; other desktop environments still need manual testing.

## Source release

`VERSION` is the version source. Update it intentionally before making a tag.
To check packaging without publishing:

```sh
python3 scripts/package_release.py
```

The archive and SHA256 file appear under `dist/releases/`. The builder uses an
explicit source allowlist, skips caches and runtime files, normalizes archive
ownership, and preserves the launcher executable bit. Extracted archives include
source, documentation, tests, branding and the showcase; native dependencies are
installed separately. This is a portable source release, not an AppImage or .deb.

When you decide to publish, commit the reviewed change and create/push a matching
`v<VERSION>` tag. The workflow creates a **draft** release. Review its files and
notes in GitHub before publishing it. Do not move or reuse a published tag.

## GitHub Pages, when ready

1. Push the reviewed repository to GitHub.
2. In **Settings → Pages → Build and deployment**, select **GitHub Actions**.
3. Review the `github-pages` environment and its allowed deployment branch.
4. Under **Actions**, choose **Deploy showcase to GitHub Pages**, select `main`,
   and click **Run workflow**.
5. Open the URL reported by its deployment environment. For this repository the
   default project URL is `https://nashvel.github.io/codex-island/`.

The manual trigger avoids publishing during initial source preparation. It can
be run again after showcase changes. A custom domain is optional and has not been
configured. Build output uses relative paths and includes `.nojekyll`.

GitHub's [custom Pages workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
explains Pages permissions and environment requirements.

## Preview locally

```sh
python3 scripts/build_site.py
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist/site
```

Visit `http://127.0.0.1:8000/`. Re-run the builder after editing `site/` or shared
assets. There are no analytics, remote fonts, account setup or build dependencies.
The island interactions on the site are explicitly simulated; they cannot start
Codex or inspect/stop visitors' services.
