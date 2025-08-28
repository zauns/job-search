# Test Suite Documentation

## Overview

This test suite covers the job matching application functionality, including AI-powered keyword extraction and resume processing. The tests are designed to work with real services rather than mocks to ensure accurate integration testing.

## Requirements

### Ollama Service

Many tests in this suite require the Ollama service to be running and properly configured. This is intentional - we removed mock implementations to ensure tests validate real AI functionality.

#### Prerequisites

1. **Ollama Installation**: Install Ollama from [https://ollama.ai](https://ollama.ai)
2. **Model Download**: Download at least one language model (e.g., `ollama pull llama2`)
3. **Service Running**: Ensure Ollama service is running (`ollama serve`)
4. **Network Access**: Ensure no firewall blocks access to Ollama service

#### Verification

To verify Ollama is properly set up, run:

```bash
# Check if Ollama is running
ollama list

# Test basic functionality
ollama run llama2 "Hello, world!"
```

### Test Categories

#### Tests Requiring Ollama

Tests marked with `@pytest.mark.requires_ollama` require Ollama to be available:

- `test_ai_matching_service.py`: AI service functionality tests
- `test_resume_ai_integration.py`: Resume service AI integration tests

These tests will be **automatically skipped** if Ollama is not available, with clear error messages explaining the requirements.

#### Tests Not Requiring Ollama

The following tests can run without Ollama:

- `test_models.py`: Database model tests
- `test_config.py`: Configuration tests
- `test_validators.py`: Input validation tests
- `test_resume_service.py`: Basic resume service tests (non-AI functionality)

## Running Tests

### Run All Tests

```bash
# Run all tests (Ollama-dependent tests will be skipped if unavailable)
pytest

# Run with verbose output
pytest -v
```

### Run Only Ollama-Independent Tests

```bash
# Skip all tests that require Ollama
pytest -m "not requires_ollama"
```

### Run Only Ollama-Dependent Tests

```bash
# Run only tests that require Ollama (will fail if Ollama unavailable)
pytest -m "requires_ollama"
```

### Force Run with Ollama Requirement

```bash
# Fail fast if Ollama is not available
pytest --tb=short -x -m "requires_ollama"
```

## Test Fixtures

### Ollama Availability Fixtures

- `ollama_availability`: Session-scoped fixture that checks Ollama once per test session
- `require_ollama`: Skips test if Ollama is not available
- `ai_service_with_ollama_check`: Provides AIMatchingService instance with availability check

### Usage Example

```python
@pytest.mark.requires_ollama
def test_ai_functionality(ai_service_with_ollama_check):
    """Test that requires Ollama to be running"""
    service = ai_service_with_ollama_check
    result = service.extract_keywords("sample text")
    assert len(result.keywords) > 0
```

## Error Messages

When Ollama is not available, tests provide clear error messages:

```
SKIPPED [1] tests/conftest.py:45: Ollama service is required but not available: Ollama connection failed: Failed to initialize Ollama client: [Errno 111] Connection refused
Please ensure:
1. Ollama is installed and running
2. At least one model is downloaded (e.g., 'ollama pull llama2')
3. Ollama service is accessible on the configured URL
4. No firewall is blocking the connection
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ollama service is not running
   - Solution: Run `ollama serve` in a terminal

2. **No Models Available**: No models downloaded
   - Solution: Run `ollama pull llama2` or another model

3. **Model Not Found**: Specific model not available
   - Solution: Check available models with `ollama list`

4. **Permission Denied**: Ollama service access restricted
   - Solution: Check firewall settings and service configuration

### Debug Mode

For detailed debugging information:

```bash
# Run with maximum verbosity
pytest -vvv --tb=long

# Show all output (including print statements)
pytest -s

# Stop on first failure
pytest -x
```

## Configuration

Test configuration is managed through:

- `pytest.ini`: Main pytest configuration
- `tests/conftest.py`: Shared fixtures and test setup
- Environment variables: Can override Ollama settings for testing

### Environment Variables

```bash
# Override Ollama model for testing
export OLLAMA_MODEL="llama2:7b"

# Override Ollama base URL
export OLLAMA_BASE_URL="http://localhost:11434"
```

## Best Practices

1. **Always use fixtures**: Use provided fixtures rather than creating service instances directly
2. **Mark Ollama tests**: Use `@pytest.mark.requires_ollama` for tests needing Ollama
3. **Handle unavailability**: Tests should gracefully skip when Ollama is unavailable
4. **Clear assertions**: Use descriptive assertion messages for better debugging
5. **Cleanup resources**: Ensure temporary files and database entries are cleaned up

## Continuous Integration

For CI/CD environments:

1. **Install Ollama**: Include Ollama installation in CI setup
2. **Download Models**: Pre-download required models
3. **Service Management**: Ensure Ollama service starts before tests
4. **Timeout Handling**: Set appropriate timeouts for AI operations
5. **Parallel Execution**: Be cautious with parallel test execution when using Ollama

Example CI configuration:

```yaml
# GitHub Actions example
- name: Setup Ollama
  run: |
    curl -fsSL https://ollama.ai/install.sh | sh
    ollama serve &
    sleep 5
    ollama pull llama2

- name: Run Tests
  run: pytest -v
```