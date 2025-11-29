# Contributing to sub-tools

Thank you for your interest in contributing to sub-tools!

## Contribution Process

### Before You Start

1. **Check for existing issues**: Search the [issue tracker](https://github.com/dohyeondk/sub-tools/issues) to see if your bug or feature request already exists.
2. **Create an issue**: If none exists, create a new issue describing:
   - For bugs: Steps to reproduce, expected vs actual behavior, environment details
   - For features: Use case, proposed implementation approach, any alternatives considered

### Making Your Contribution

1. **Fork the repository**: Click the "Fork" button on GitHub to create your own copy.

2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/sub-tools.git
   cd sub-tools
   ```

3. **Set up development environment:**
   ```bash
   uv sync
   ```

4. **Create a feature branch:**
   ```bash
   git checkout -b feature/issue-123-add-new-feature
   # or
   git checkout -b fix/issue-456-fix-bug-description
   ```
   
   Branch naming convention:
   - `feature/issue-N-description` for new features
   - `fix/issue-N-description` for bug fixes
   - `docs/issue-N-description` for documentation updates
   - `refactor/issue-N-description` for code refactoring

5. **Make your changes:**
   - Write clean, readable code following existing patterns
   - Add tests for new functionality
   - Update documentation if needed
   - Run tests: `uv run pytest`

6. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: Add new feature (#123)"
   # or
   git commit -m "fix: Resolve bug in transcription (#456)"
   ```
   
   Commit message format:
   - `feat: Description (#issue-number)` for new features
   - `fix: Description (#issue-number)` for bug fixes
   - `docs: Description (#issue-number)` for documentation
   - `refactor: Description (#issue-number)` for refactoring
   - `test: Description (#issue-number)` for test updates
   - `chore: Description (#issue-number)` for maintenance tasks

7. **Push to your fork:**
   ```bash
   git push origin feature/issue-123-add-new-feature
   ```

8. **Create a Pull Request:**
   - Go to the [original repository](https://github.com/dohyeondk/sub-tools)
   - Click "New Pull Request"
   - Select `main` as the base branch
   - Select your feature branch as the compare branch
   - Fill out the PR template:
     - **Title**: Brief description (e.g., "Add support for custom output formats")
     - **Description**: 
       - Link to the issue: "Closes #123" or "Fixes #456"
       - Describe what changed and why
       - Include any testing steps or screenshots if relevant
       - Note any breaking changes

### Pull Request Guidelines

- Target the `main` branch for all PRs
- Link the related issue(s) using keywords like "Closes #123", "Fixes #456", or "Resolves #789"
- Ensure all tests pass before requesting review
- Keep PRs focused on a single issue or feature
- Update documentation if you're changing functionality
- Be responsive to review feedback

### Code Review Process

1. Maintainers will review your PR
2. Address any requested changes by pushing new commits to your branch
3. Once approved, a maintainer will merge your PR
4. Your contribution will be included in the next release

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
