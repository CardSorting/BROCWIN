# Contributing to BROCWIN

BROCWIN is a frozen research project. Documentation, citation corrections, accessibility improvements and preservation metadata can be proposed now. Runtime/integration edits, builds, captures, runtime tests, native-service or SQL changes require MAJO to explicitly reopen engineering. A GitHub issue or pull request does not release that freeze.

Read [README](README.md), [the walkthrough](docs/walkthrough.md), [the licensing scope](LICENSES/README.md), [the code of conduct](CODE_OF_CONDUCT.md) and [governance](GOVERNANCE.md).

1. Describe a concrete observation or documentation problem. Cite a retained record and its build identity; separate hypotheses from results.
2. Make a small, reviewable change in a branch. Preserve contributor credit, third-party notices and original evidence. Add corrections or a new edition to sealed artifacts rather than rewriting them.
3. Run `python scripts/check_repository.py` from this directory. Full local knowledge verification additionally requires retained dependency/evidence holdings; see the walkthrough. Do not run runtime experiments to satisfy a documentation PR.
4. Describe what changed, why, validation performed and unavailable artifacts. Do not include credentials, SQL dumps, original binaries, game screenshots or unchecked dependency patches.
5. Certify your right to submit the work under its applicable license. Add a `Signed-off-by: Your Name <your-email>` trailer for a new commit when you can make that certification. The [DCO 1.1](https://developercertificate.org/) describes that certification; it is not copyright assignment. Do not invent identity or sign on someone else's behalf.

AI-assisted work must identify the responsible contributor and disclose substantial generated/reconstructed content in its PR. The contributor remains responsible for verifying claims, provenance and license compatibility. A successful API fixture is not application acceptance, and a newer build cannot inherit an older capture's success.

Documentation CI checks repository conventions and links in the newly prepared community documents. It deliberately does not download dependencies, build the runtime, launch the client or provision services. There is no automatic merge or release promise. [SUPPORT](SUPPORT.md) explains the currently unconfigured public channels.
