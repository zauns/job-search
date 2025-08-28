# Design Document

## Overview

This design outlines the removal of all mock Ollama implementations and fallback mechanisms from the job matching application. Since Ollama is now properly integrated and working, we can simplify the codebase by removing unnecessary complexity around fallback scenarios and mock testing infrastructure.

## Architecture

The simplified architecture will have these key changes:

1. **AI Matching Service**: Remove fallback keyword extraction and rule-based approaches
2. **Test Suite**: Remove all Ollama mocking and use real Ollama service for integration tests
3. **Configuration**: Remove fallback-related settings and error handling paths
4. **Documentation**: Update task specifications to reflect simplified architecture

## Components and Interfaces

### AIMatchingService Modifications

**Removed Components:**
- `fallback_keywords` dictionary
- `_extract_keywords_fallback()` method
- Fallback logic in `extract_resume_keywords()`
- `fallback_used` field from `KeywordExtractionResult`
- Fallback references in `get_model_info()`

**Simplified Interface:**
```python
class AIMatchingService:
    def __init__(self, model_name: Optional[str] = None):
        # Simplified initialization - requires Ollama
        
    def extract_resume_keywords(self, latex_content: str) -> KeywordExtractionResult:
        # Direct Ollama extraction only
        
    def get_model_info(self) -> Dict[str, str]:
        # Ollama-only status information
```

### KeywordExtractionResult Simplification

**Updated Structure:**
```python
@dataclass
class KeywordExtractionResult:
    keywords: List[str]
    confidence: float
    language_detected: str
    # Removed: fallback_used field
```

### Test Suite Modifications

**Removed Components:**
- All `@patch('job_matching_app.services.ai_matching_service.ollama')` decorators
- Mock Ollama response setups
- Fallback testing scenarios
- Mock client assignments

**New Approach:**
- Tests will use real Ollama service
- Tests will require Ollama to be running and configured
- Clear error messages when Ollama is unavailable during testing

## Data Models

### Configuration Changes

Remove fallback-related configuration options and ensure Ollama is required:

```python
# Removed settings
- ollama_enabled (always assumed true)
- fallback timeout configurations
- fallback keyword lists

# Required settings
- ollama_model (must be available)
- ollama_temperature
- ollama_base_url (if needed)
```

## Error Handling

### Simplified Error Strategy

1. **Ollama Unavailable**: Raise `OllamaConnectionError` immediately
2. **Model Not Found**: Raise specific model configuration errors
3. **Generation Failures**: Raise Ollama-specific errors with clear messages
4. **Test Failures**: Clear messages indicating Ollama service requirements

### Error Flow

```
Service Initialization
├── Ollama Available? ──No──> Raise OllamaConnectionError
└── Yes ──> Continue

Keyword Extraction
├── Ollama Responds? ──No──> Raise OllamaConnectionError  
└── Yes ──> Return Results
```

## Testing Strategy

### Integration Testing Approach

1. **Prerequisites**: Tests require running Ollama service
2. **Setup**: Verify Ollama availability before test execution
3. **Cleanup**: No mock cleanup needed
4. **Assertions**: Test actual Ollama responses and behavior

### Test Categories

1. **Service Integration Tests**: Real Ollama communication
2. **Error Handling Tests**: Actual Ollama failure scenarios
3. **Multilingual Tests**: Real language detection and processing
4. **Performance Tests**: Actual response time measurements

### Test Environment Requirements

- Ollama service running locally or in test environment
- Required models downloaded and available
- Network connectivity to Ollama service
- Proper Ollama configuration for test scenarios

## Implementation Phases

### Phase 1: Remove Fallback Logic
- Remove fallback methods from AIMatchingService
- Update KeywordExtractionResult dataclass
- Simplify service initialization

### Phase 2: Update Test Suite
- Remove all Ollama mocking
- Update test fixtures to use real Ollama
- Add Ollama availability checks to test setup

### Phase 3: Clean Configuration
- Remove fallback-related settings
- Update error messages
- Simplify service info responses

### Phase 4: Update Documentation
- Remove fallback references from task specifications
- Update error handling documentation
- Clarify Ollama requirements