# CLAUDE.md

## The situation
 
Take-home assignment for an Applied AI Solutions Engineer role at Tomoro. One week, ~10-15 hours of effort, submitted as a PR to main.
 
**Build:** an LLM-driven prototype that answers conversational questions over financial documents, evaluated on a cleaned ConvFinQA dataset.
 
**Graded on:** code quality (~75%), report (~25%), and judgment throughout. The brief explicitly says *"complexity does not equal sophistication"* and *"blindly reimplementing the paper with an updated model is not sufficient."*

## Reading order for a new agent
 
Stop and read these before doing anything:
 
1. **This file.**
2. **`TASK.md`** — the actual brief. Read carefully; there are details that matter.
3. **`dataset.md`** — what the cleaned data actually looks like (may differ from the paper).
4. **`README.md`** — repo conventions and any boilerplate they provided.
5. **`convfinqa_paper.pdf`** — context for the task. Sections 5, 6, and the error analyses (5.3, 6.3) are the highest-value parts. Skim the rest.
6. **Existing code** — whatever boilerplate is already there. Match its style.
If any of these don't exist yet, that's a signal something is missing — flag it before proceeding.

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
