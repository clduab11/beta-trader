# Universal Coding Style Guide
# ------------------------------------------------------------------
# Focused on Python, Rust, and General Engineering Excellence.

## 1. General Principles
-   **SOLID**: Adhere to Single Responsibility, Open-Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion.
-   **DRY**: Don't Repeat Yourself. Extract common logic.
-   **KISS**: Keep It Simple, Stupid. Avoid over-engineering.

## 2. Python (3.12+)
-   **Typing**: Strict type hints are **mandatory**. Use `typing.Annotated`, `typing.Protocol`, and `pydantic`.
-   **Async**: Prefer `asyncio` for I/O-bound operations.
-   **Docstrings**: Google Style docstrings for all public functions/classes.
-   **Tooling**: Compatible with `ruff` and `black`.

## 3. Rust (2021 Edition)
-   **Safety**: Avoid `unsafe` unless absolutely necessary (benchmark imperative).
-   **Error Handling**: Use `Result<T, E>` and `?` operator. No `unwrap()` in production code.
-   **Async**: Use `tokio` runtime typical patterns.
-   **Clippy**: Code must be Clippy-clean.

## 4. Documentation
-   **Architecture**: Update `README.md` or `docs/` if architecture changes.
-   **Comments**: Explain *why*, not *what*. Code should be self-documenting.

## 5. Testing
-   **Unit Tests**: Co-locate with code in Rust module tests. Use `pytest` for Python.
-   **Integration**: Separate integration tests folder.
