# Build package .whl and .tar.gz files
build:
    uv build
    @command -v scdoc >/dev/null 2>&1 && { scdoc < man/updall.1.scdoc > dist/updall.1; echo 'Built manpage scdoc.1'; } || :
    @command -v scdoc >/dev/null 2>&1 && { scdoc < man/updall.5.scdoc > dist/updall.5; echo 'Built manpage scdoc.5'; } || :

# Run tests and show package coverage
test:
    uv run pytest --cov=updall --cov-report=term-missing

# Push to Github along with tags that track pushed commits
push:
    git push origin
    if git describe --tags --exact-match >/dev/null 2>&1; then git push --tags; fi
