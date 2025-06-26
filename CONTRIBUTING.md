# Contributing to PDF Assistant Chatbot

We welcome contributions to the PDF Assistant Chatbot! Whether it's a new feature, a bug fix, or an improvement to the documentation, your help is appreciated.

Please take a moment to review this document to understand how to contribute effectively.

## 🌟 How Can I Contribute?

### 🐛 Reporting Bugs

* **Check existing issues**: Before submitting a new bug report, please check if the issue has already been reported.
* **Use the Bug Report Template**: Please use the provided `bug_report.md` template for submitting bug reports. This ensures all necessary information is included.

### ✨ Suggesting Enhancements

* **Use the Feature Request Template**: Please use the provided `feature_request.md` template for suggesting new features or enhancements.

### ❓ Asking Questions

* **Use the Question Template**: If you have a question about the project, its usage, or anything else, please use the provided `question.md` template.

### 💡 Code Contributions

#### 1. Fork the Repository

First, fork the `PDF-Assistant-Chatbot` (or the current correct repository name, e.g., `Chatbot_Pinecone_flask_backend` if it hasn't been renamed yet) repository to your GitHub account.

#### 2. Clone Your Fork

```bash
git clone https://github.com/YOUR_USERNAME/Chatbot_Pinecone_flask_backend.git
# Replace YOUR_USERNAME and ensure Chatbot_Pinecone_flask_backend is the correct repo name
cd Chatbot_Pinecone_flask_backend
# Or the actual directory name created by the clone
```

#### 3. Set Up Your Environment

*   **Create a Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
*   **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-dev.txt # For linters, testing tools
    ```

#### 4. Create a Branch

Create a new branch for your feature or bug fix:
```bash
git checkout -b feature/your-feature-name  # For new features
# or
git checkout -b bugfix/issue-description   # For bug fixes
```

#### 5. Make Your Changes

*   Write clean, readable, and well-commented code.
*   Follow the existing code style and conventions.
*   Ensure your changes are focused on the specific feature or bug.

#### 6. Run Linters and Formatters

Before committing, ensure your code adheres to the project's linting and formatting standards:
```bash
make lint
make format  # To automatically format
```
This typically involves running tools like Flake8, Black, and isort.

#### 7. Run Tests

Ensure all existing tests pass and, if you're adding a feature or fixing a bug, add new tests to cover your changes:
```bash
make test
# or
pytest
```

#### 8. Commit Your Changes

Write clear, concise, and descriptive commit messages.
```bash
git add .
git commit -m "feat: Implement X feature"
# or
git commit -m "fix: Resolve Y bug in Z component"
# (Consider using Conventional Commits style if adopted by the project)
```

#### 9. Push to Your Fork

Push your changes to your forked repository:
```bash
git push origin feature/your-feature-name
```

#### 10. Open a Pull Request (PR)

*   Go to the original repository on GitHub.
*   You should see a prompt to create a Pull Request from your recently pushed branch.
*   Use the Pull Request template (`.github/PULL_REQUEST_TEMPLATE.md`) if available.
*   Clearly describe the changes you've made, why they were made, and link any relevant issues (e.g., "Closes #123").
*   Ensure your PR is made against the `main` or `dev` branch of the upstream repository, as appropriate.

## Code Style and Conventions

*   Follow [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/).
*   Use type hinting where appropriate.
*   Keep lines under a reasonable length (e.g., 88 characters as per Black's default).
*   Write docstrings for all public modules, classes, and functions.

## Questions?

If you have any questions about contributing, feel free to open an issue using the "Question" template or reach out to the maintainers.

Thank you for your interest in contributing to the PDF Assistant Chatbot!