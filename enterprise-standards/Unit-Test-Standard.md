# Unit Test Standard — Master Table

> **Tech Lead / Principal Engineer Reference | CMMI L3 Aligned | AI/GenAI/RAG Ready**
>
> Ensures code correctness at the function/class level with fast, isolated, repeatable tests.

---

## Master Control Table

| # | Unit Test Area | Purpose (Why) | Standard Process (How) | Mandatory Rules / Controls | Evidence / Artifacts |
|---|---------------|---------------|------------------------|---------------------------|---------------------|
| 1 | **Test Scope Definition** | Focus tests correctly | Test single unit in isolation | No external dependencies | Scope guidelines |
| 2 | **Coverage Requirements** | Ensure thoroughness | Define coverage targets | Minimum 80% line coverage | Coverage reports |
| 3 | **Test Naming Convention** | Improve readability | Descriptive test names | test_[what]_[condition]_[expected] | Code review |
| 4 | **Test Structure (AAA)** | Standardize format | Arrange-Act-Assert | Clear separation | Code standards |
| 5 | **Test Isolation** | Prevent coupling | No shared state | Each test independent | Test review |
| 6 | **Mocking Strategy** | Control dependencies | Mock external dependencies | Mocks at boundaries | Mock guidelines |
| 7 | **Test Data Management** | Enable repeatability | Use fixtures/factories | No hardcoded magic values | Test data patterns |
| 8 | **Edge Case Coverage** | Prevent bugs | Test boundaries | Null, empty, max values | Coverage analysis |
| 9 | **Error Path Testing** | Handle failures | Test error conditions | Exception paths covered | Error test evidence |
| 10 | **Assertion Quality** | Meaningful failures | Specific assertions | One logical assertion per test | Assertion guidelines |
| 11 | **Test Performance** | Fast feedback | Tests run quickly | < 100ms per test | Test timing reports |
| 12 | **Determinism** | Prevent flakiness | No random/time dependencies | Tests always repeatable | Flaky test tracking |
| 13 | **CI/CD Integration** | Automate testing | Run on every commit | Block on failures | CI configuration |
| 14 | **Coverage Enforcement** | Maintain quality | Gate on coverage | Block below threshold | CI gates |
| 15 | **Test Documentation** | Explain intent | Document complex tests | Why, not what | Code comments |
| 16 | **Parameterized Tests** | Reduce duplication | Use data-driven tests | Multiple inputs, one test | Parameterized examples |
| 17 | **Test Maintenance** | Keep tests current | Update with code changes | No dead tests | Test review process |
| 18 | **Mutation Testing** | Validate test quality | Detect weak tests | Mutation score tracked | Mutation reports |
| 19 | **AI/Prompt Testing** | Validate AI logic | Test prompt construction | Template tests | AI unit tests |
| 20 | **Business Logic Focus** | Prioritize value | Test critical paths | Business rules covered | Priority matrix |
| 21 | **Test Refactoring** | Maintain quality | Refactor test code | DRY principles | Code review |
| 22 | **Negative Testing** | Prevent misuse | Test invalid inputs | Validation tested | Negative test cases |
| 23 | **Regression Prevention** | Catch bugs | Add tests for bugs | Bug = test first | Bug fix process |
| 24 | **Test Reporting** | Track quality | Generate reports | Trends visible | Test dashboards |
| 25 | **Continuous Improvement** | Evolve practices | Review test effectiveness | Quarterly review | Improvement backlog |

---

## Coverage Requirements

| Code Type | Minimum Coverage | Target Coverage |
|-----------|-----------------|-----------------|
| Business Logic | 90% | 95% |
| API Handlers | 85% | 90% |
| Utilities | 80% | 90% |
| Data Access | 80% | 85% |
| Configuration | 70% | 80% |
| Generated Code | Excluded | Excluded |

---

## Test Naming Convention

```
test_[unit]_[scenario]_[expected_result]
```

Examples:
- `test_calculate_total_with_discount_returns_reduced_price`
- `test_validate_email_with_invalid_format_raises_error`
- `test_user_service_get_user_not_found_returns_none`

---

## Test Structure (AAA Pattern)

```python
def test_calculate_discount_with_valid_coupon_applies_percentage():
    # Arrange
    price = 100.00
    coupon = Coupon(code="SAVE20", discount_percent=20)

    # Act
    result = calculate_discount(price, coupon)

    # Assert
    assert result == 80.00
```

---

## AI / GenAI Unit Test Add-Ons

| Test Area | What to Test |
|-----------|--------------|
| **Prompt Templates** | Variable substitution, escaping |
| **Token Counting** | Token estimation accuracy |
| **Input Validation** | Content length, format validation |
| **Output Parsing** | Response parsing, extraction |
| **Error Handling** | API error handling, retries |
| **Cost Calculation** | Token-to-cost conversion |
| **Chunking Logic** | Text splitting, overlap |

---

## AI Prompt Unit Test Example

```python
def test_prompt_template_substitutes_variables():
    # Arrange
    template = PromptTemplate(
        "Answer the question: {question}\nContext: {context}"
    )

    # Act
    result = template.render(
        question="What is Azure?",
        context="Azure is Microsoft's cloud platform."
    )

    # Assert
    assert "What is Azure?" in result
    assert "Azure is Microsoft's cloud platform" in result


def test_chunk_text_respects_max_tokens():
    # Arrange
    long_text = "word " * 1000
    max_tokens = 100

    # Act
    chunks = chunk_text(long_text, max_tokens=max_tokens)

    # Assert
    for chunk in chunks:
        assert count_tokens(chunk) <= max_tokens
```

---

## Mocking Guidelines

| Dependency | Mock? | Reason |
|------------|-------|--------|
| External APIs | Yes | Isolation, speed |
| Database | Yes | Speed, isolation |
| File system | Yes | Speed, isolation |
| Time/dates | Yes | Determinism |
| Random values | Yes | Determinism |
| Internal classes | Usually No | Test real behavior |

---

## Unit Test Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Testing implementation | Brittle tests | Test behavior |
| Multiple assertions | Unclear failures | One assertion |
| Shared state | Test pollution | Isolate tests |
| Testing private methods | Over-specification | Test public API |
| Ignoring edge cases | Hidden bugs | Comprehensive cases |
| Slow tests | Slow feedback | Mock dependencies |

---

## Test Quality Checklist

```markdown
Test Design:
- [ ] Tests single unit of code
- [ ] No external dependencies
- [ ] Follows AAA pattern
- [ ] Descriptive name
- [ ] Covers happy path

Coverage:
- [ ] Edge cases covered
- [ ] Error paths tested
- [ ] Boundary conditions tested
- [ ] Null/empty inputs handled

Quality:
- [ ] Runs in < 100ms
- [ ] Deterministic (no flakiness)
- [ ] Clear assertion messages
- [ ] No test duplication
```

---

## Parameterized Test Example

```python
@pytest.mark.parametrize("input_email,expected_valid", [
    ("user@example.com", True),
    ("user.name@example.co.uk", True),
    ("invalid-email", False),
    ("", False),
    (None, False),
    ("user@", False),
    ("@example.com", False),
])
def test_validate_email(input_email, expected_valid):
    result = validate_email(input_email)
    assert result == expected_valid
```

---

## Common Failures (Reality Check)

| Anti-Pattern | Consequence |
|--------------|-------------|
| Tests that never fail | False confidence |
| Mocking everything | Testing mocks, not code |
| No edge case coverage | Bugs in production |
| Slow unit tests | Developers skip them |
| Flaky tests | Tests get ignored |

---

## CI/CD Integration

| Gate | Threshold | Action |
|------|-----------|--------|
| All tests pass | 100% | Block merge |
| Line coverage | > 80% | Block merge |
| Branch coverage | > 75% | Warn |
| New code coverage | > 90% | Block merge |
| Test execution time | < 5 min total | Optimize |

---

## Testing Framework Standards

| Language | Framework | Mocking |
|----------|-----------|---------|
| Python | pytest | pytest-mock, unittest.mock |
| TypeScript | Jest | Jest mocks |
| Go | testing | testify, gomock |
| Java | JUnit 5 | Mockito |
| C# | xUnit | Moq |

---

## Test File Organization

```
src/
  services/
    user_service.py
tests/
  unit/
    services/
      test_user_service.py
  integration/
    ...
  fixtures/
    user_fixtures.py
```

---

## Executive Summary

> **Unit Testing ensures code correctness at the smallest testable level—providing fast feedback, enabling refactoring, and preventing regressions.**

---

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Classification | Internal / Engineering Standard |
| Applicable To | All code |
| Framework Alignment | CMMI L3, ISO 42001 |
