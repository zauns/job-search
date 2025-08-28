# Implementation Plan

- [x] 1. Remove fallback logic from AIMatchingService








  - Remove `fallback_keywords` dictionary from class initialization
  - Remove `_extract_keywords_fallback()` method completely
  - Remove fallback logic from `extract_resume_keywords()` method
  - Update `_initialize_client()` to require Ollama availability
  - _Requirements: 2.1, 2.2, 3.1_

- [x] 2. Simplify KeywordExtractionResult dataclass





  - Remove `fallback_used` field from dataclass definition
  - Update all instantiations to remove fallback_used parameter
  - Update method signatures that reference fallback_used
  - _Requirements: 2.1, 3.1_

- [x] 3. Update service info and error handling





  - Remove fallback references from `get_model_info()` method
  - Simplify error messages to focus on Ollama-specific issues
  - Update exception handling to raise OllamaConnectionError directly
  - _Requirements: 2.2, 3.2, 4.3_

- [x] 4. Remove Ollama mocks from AI matching service tests





  - Remove all `@patch('job_matching_app.services.ai_matching_service.ollama')` decorators
  - Remove mock Ollama setup code from test methods
  - Remove mock client assignments and mock response configurations
  - Update tests to use real Ollama service
  - _Requirements: 1.1, 1.2_

- [x] 5. Remove Ollama mocks from resume AI integration tests





  - Remove all Ollama mocking decorators and setup code
  - Remove mock generate responses and mock client assignments
  - Update tests to work with real Ollama service
  - Remove fallback testing scenarios
  - _Requirements: 1.1, 1.2_

- [x] 6. Add Ollama availability checks to test setup





  - Create test fixtures that verify Ollama service availability
  - Add clear error messages when Ollama is unavailable during testing
  - Update test documentation to specify Ollama requirements
  - _Requirements: 1.3, 4.1_

- [x] 7. Update task documentation to remove fallback references





  - Remove references to "mock ollama" and "fallback mechanism" from existing task specifications
  - Update error handling documentation to focus on Ollama-specific scenarios
  - Update future task planning to assume Ollama availability
  - _Requirements: 4.1, 4.2, 4.3_