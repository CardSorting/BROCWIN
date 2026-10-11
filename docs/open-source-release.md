# Open-source repository and release preparation

This is a prepared community/documentation scaffold, not a remote publication or a claim that the entire inherited workspace is freely redistributable. The engineering freeze remains in force.

## Strategy and references

The layout follows familiar conventions: a clear README and walkthrough, license and third-party notices, contributor guidance, conduct/security/support policies, governance, citation metadata, change history, issue/PR templates and focused CI. [GitHub's repository guidance](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories) describes these entry points and host security controls. [VS Code's contributor guide](https://github.com/microsoft/vscode/blob/main/CONTRIBUTING.md) exemplifies routing contributors to detailed workflows; [Rust's copyright inventory](https://github.com/rust-lang/rust/blob/main/COPYRIGHT) exemplifies separate attribution records. This preparation borrows structure, not their project names, support teams, license choices, CI badges or promises.

MIT was selected to continue the existing parent license, rather than introducing an incompatible licensing change. Retained third-party declarations and excluded inputs are documented in [LICENSES](../LICENSES/README.md). The [MIT text and notice requirement](https://choosealicense.com/licenses/mit/) provide context; this file does not establish new rights in unlicensed material.

## Distribution boundary

| Include after review | Keep in private/local custody |
| --- | --- |
| Eligible integration/helper source and its license notices | Original client/server executables, DLLs, Microsoft-derived platform bytes and generated Wasm |
| Authored research, community files and reviewed figures/PDFs | Game archives/assets/fonts/logos, extracted content and screenshots with mixed rights |
| Dependency pin and provenance descriptions | Third-party installed trees, native state, SQL backups and `.env` |
| A rights-reviewed patch when upstream terms and incorporated content are resolved | The current dependency patch and frozen copied sources until that review is complete |
| Hash/path indexes where privacy review permits them | Raw logs/captures/records containing accounts, tokens, private paths or operational data |

The source checkout intentionally omits some artifacts required for reproduction. Do not describe it as a runnable turnkey distribution. Sealed research bundles remain local evidence objects; adding ignore rules does not change their contents or licensing.

## Current decisions still needed

1. Name the standalone repository owner, canonical URL, technical/release reviewers and moderator. No fake owner, URL, CODEOWNERS rule, contact email or support SLA is inserted.
2. Establish private security and conduct reporting contacts before opening community participation. Enable GitHub private vulnerability reporting, secret scanning and push protection where available.
3. Resolve Wine-Assembly's retained MIT LICENSE versus ISC package metadata. Preserve the actual notices; do not rewrite the upstream declaration or relabel all upstream bytes as BROCWIN-owned.
4. Review original/platform/game-content permissions and every proposed patch/vendor artifact. Inventory exact transitive dependencies if binaries or tools will be redistributed.
5. Review Git history as well as the proposed tree for private/large/unlicensed objects. A source-only export from an explicit selection avoids accidentally publishing the parent workspace's inherited history; actual initialization, staging, commit and push are separate deliberate operations.
6. Decide the public artifact set: authored source/docs only, selected publication PDFs, or a separately reviewed archival release. Define which evidence is accessible and who holds excluded material.

These decisions prevent invented commitments; they do not block local preparation of the concrete files now provided. Public distribution and engineering reopening are distinct authorities.

## Suggested owner walkthrough

In a **separate selected source-release directory**, copy only reviewed eligible files, preserving this directory's `browser/`, `wiki/` and publication structure. Include all license/NOTICE files. Resolve historical links to omitted holdings with a custody explanation or separately reviewed evidence location; never fabricate a passing result because a report is missing.

Run `python scripts/check_repository.py`. Review `git status --short` and `git check-ignore -v` in that selected directory before staging. Inspect the actual proposed file list and file sizes. Do not use `git add .` against the original parent workspace, which has unrelated inherited changes. `.gitignore` cannot remove secrets already committed; any discovered exposure needs a separately authorized response.

Create a repository and publish only after the hosting/rights decisions above are resolved. At the new root, `.github/ISSUE_TEMPLATE`, `.github/PULL_REQUEST_TEMPLATE.md` and `.github/workflows/documentation.yml` become active. While nested under the existing root, these are prepared files and do not override the parent's active workflows/templates.

Use protected branches, reviewed pull requests and the `community-files` status check. A hosted action passing this check proves only documentation-scaffold integrity. Enable Discussions only if someone will moderate them. Add real repository URLs/contact routes and CODEOWNERS only after owners are known. Automated dependency upgrades, runtime CI and releases remain disabled during the freeze; do not introduce a workflow that downloads/builds or resumes experiments.

The prepared workflow follows the current v7 usage shown by the official [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python) repositories, checked 2026-10-11. It has read-only repository permissions and disables persisted checkout credentials. The hosting owner should pin reviewed action commits for its release policy; no hosted run or action execution is claimed by this local preparation.

For a future release, record an explicit file inventory and hashes, license inventory, excluded holdings, reproduction limitations and review owner. Tag only the reviewed source commit. A source tag, knowledge edition and publication edition identify different artifacts; use names that keep them distinct. No tag or release is created by this guide.

## Current preparation verification

The community checker verifies the added documents and copied license texts. Retained knowledge/publication checks verify that this preparation did not modify frozen runtime records or sealed publications. New files remain local and unstaged; no remote settings, messages or deployments are performed.
