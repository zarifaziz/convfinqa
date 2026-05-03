## Architecture Conventions

- Use Domain Driven Design with separate layers for `domain`, `services`, and `repository`

## Python Conventions

- Use `uv` for dependency management
- Use `pydantic-settings` for configuration (`settings.py` reads from `.env`)
- Use `pydantic` for types, data modelling, and validation
- Use `loguru` for logging
- Use `pathlib` for file paths
- Use `ruff` for linting/formatting
- Use `typer` for CLI

## Testing

```bash
uv run pytest
```
