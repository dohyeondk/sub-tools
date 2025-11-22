# Contributing to sub-tools

Thank you for your interest in contributing to sub-tools!

## Version Bumping

This project uses semantic versioning (MAJOR.MINOR.PATCH). The version is maintained in `pyproject.toml`.

### How to Bump the Version

1. **Determine the version bump type:**
   - **PATCH** (0.7.2 → 0.7.3): Bug fixes, minor improvements, documentation updates
   - **MINOR** (0.7.2 → 0.8.0): New features, backwards-compatible changes
   - **MAJOR** (0.7.2 → 1.0.0): Breaking changes, major API changes

2. **Update the version in `pyproject.toml`:**
   
   Edit the version field:
   ```toml
   [project]
   name = "sub-tools"
   version = "0.7.3"  # Update this line
   ```

3. **Sync the lock file:**
   ```bash
   uv sync
   ```

4. **Commit the version change:**
   ```bash
   git add pyproject.toml uv.lock
   git commit -m "chore: Bump version to 0.7.3"
   ```

5. **Create a git tag:**
   ```bash
   git tag v0.7.3
   git push origin v0.7.3
   ```

6. **Create a GitHub release:**
   ```bash
   gh release create v0.7.3 --title "v0.7.3" --notes "## What's Changed
   
   ### Features
   - New feature description
   
   ### Fixes
   - Bug fix description
   
   **Full Changelog**: https://github.com/dohyeondk/sub-tools/compare/v0.7.2...v0.7.3"
   ```

### Version Bump Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Run `uv sync` to update the lock file
- [ ] Commit both `pyproject.toml` and `uv.lock`
- [ ] Create and push a git tag
- [ ] Create a GitHub release with changelog
- [ ] Ensure all tests pass before releasing
