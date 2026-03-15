# Contributing

## Branching workflow

`main` is protected — direct pushes are not allowed. All changes must go through a PR.

```
main          ← protected, only merged via PR after CI passes
  └── feat/my-feature   ← your work branch
  └── fix/some-bug
  └── chore/update-deps
```

### Steps

1. **Create a branch** from `main`:
   ```bash
   git checkout main && git pull
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes**, commit using [conventional commits](https://www.conventionalcommits.org/):
   ```
   feat: add semantic search filters
   fix: handle empty PDF gracefully
   chore: update fastembed to 0.8
   ```

3. **Push and open a PR** targeting `main`:
   ```bash
   git push -u origin feat/your-feature-name
   gh pr create --base main
   ```

4. **CI must pass** before merging (GitHub enforces this):
   - `Frontend` — TypeScript typecheck + Vitest tests
   - `Backend` — pytest suite

5. **Merge** once CI is green (squash or merge commit, no force-push to main).

## Running tests locally

```bash
# Frontend
npm test

# Backend
cd backend
python -m pytest tests/ -v
```

## Branch naming

| Prefix | Use for |
|--------|---------|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `chore/` | Maintenance, deps, config |
| `docs/` | Documentation only |
| `refactor/` | Code cleanup with no behaviour change |
