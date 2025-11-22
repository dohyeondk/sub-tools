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
   git push origin main --tags
   ```
