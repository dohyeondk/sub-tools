---
name: release-library
description: "Release the sub-tools Python library by selecting the next SemVer version, synchronizing pyproject.toml and uv.lock, running the test and build checks, creating GitHub release notes, pushing the release tag, and verifying the tag-triggered PyPI workflow. Use when asked to cut, publish, tag, or release a sub-tools library version."
---

# Release Library

Use this skill from the repository root to make an auditable `sub-tools` release. The package is published by `.github/workflows/publish.yml` when a `v*` tag is pushed.

## Release policy

- Read the version from `[project] version` in `pyproject.toml` and inspect the latest stable `vMAJOR.MINOR.PATCH` tag. Default to a patch bump; use a minor, major, prerelease, or explicitly supplied version only when the user requests it.
- Check `git status --short --branch` before editing. Preserve unrelated user changes and stop if the worktree is not clean enough to identify the release files safely.
- Confirm that the candidate version and tag do not already exist locally or on `origin`. Stop rather than overwrite an existing tag or release.
- Keep the current branch name. Release only from the intended release branch or from a commit explicitly authorized for release; do not force-push or silently merge branches.

## Prepare and validate

1. Review `git log PREVIOUS_TAG..HEAD` and the relevant diff to understand what the release contains.
2. Update only the project version in `pyproject.toml` unless the user requests other release changes.
3. Run `uv sync` immediately after changing `pyproject.toml`; commit the resulting `uv.lock` update with it.
4. Run `uv run pytest -m "not slow"`, `uv build`, and `git diff --check`. Inspect the staged diff and verify that the package version in both `pyproject.toml` and `uv.lock` is the candidate version.
5. Remove or leave ignored build artifacts as the repository conventions require. Never stage generated files that are not part of the release.

Do not create a tag or GitHub release when code or build validation fails. If a test fails only because a documented third-party fixture or network service is unavailable, capture the exact error, run the remaining local tests, and proceed only when the user has explicitly authorized the release; report the caveat.

## Commit, tag, and publish

1. Stage the intentional release files, normally `pyproject.toml`, `uv.lock`, and any requested release-skill/documentation change. Commit with `chore: Bump version to X.Y.Z`.
2. Push the release commit to the intended remote branch without force-pushing. Keep the branch name unchanged.
3. Create an annotated tag with `git tag -a vX.Y.Z -m "Release vX.Y.Z"` and push it with `git push origin vX.Y.Z`.
4. Create the published GitHub release with generated notes:

   ```bash
   gh release create vX.Y.Z --repo dohyeondk/sub-tools \
     --title "vX.Y.Z" --generate-notes
   ```

   Inspect the resulting release page/body and correct it with `gh release edit` if the generated notes omit important user-visible changes. Changelist entries do not need manual author attribution. Do not create a second release for an existing tag.

## Verify delivery

- Confirm the tag points at the release commit and the GitHub release is published rather than draft.
- Find the tag-triggered run with `gh run list --repo dohyeondk/sub-tools --workflow publish.yml --limit 5` and inspect it with `gh run view`. Wait for the run to finish when practical.
- Report the release URL, tag, commit, test/build results, and publish workflow result. If the workflow fails, include the failing job/log and do not claim that PyPI publication succeeded.
