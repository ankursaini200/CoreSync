# Contributing to CoreSync

Thank you for your interest in contributing to **CoreSync**! This project is an open-source Operating Systems research and educational workstation simulator.

---

## 1. Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please be respectful and constructive in all communications and code reviews.

---

## 2. How to Contribute

### Reporting Bugs
- Use the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md).
- Clearly describe the steps to reproduce, observed vs expected behavior, system architecture, and attach logs from `logs/app.log`.

### Suggesting Enhancements
- Use the [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md).
- Detail the use case, pedagogical or experimental value, and target subsystem.

### Pull Requests
1. **Fork and branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Follow Architectural Invariants**:
   - Workers must NEVER import PySide6 or Qt.
   - Multiprocessing MUST use `spawn`.
   - Never divide physical seconds by virtual clock ticks.
   - Maintain the zero orphan process guarantee.
3. **Add Tests**:
   - Every bugfix or new feature must include automated unit/integration tests in `tests/`.
4. **Run the full test suite**:
   ```bash
   pytest tests/
   ```
   All tests must pass before submitting a PR.
5. **Open a PR**:
   - Fill in the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md).

---

## 3. License

By contributing to CoreSync, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

