# Build package .whl and .tar.gz files
build:
    uv build

# Run tests and show package coverage
test:
    uv run pytest --cov=updall --cov-report=term-missing

# Push to Github along with tags that track pushed commits
push:
    git push origin
    if git describe --tags --exact-match >/dev/null 2>&1; then git push --tags; fi
