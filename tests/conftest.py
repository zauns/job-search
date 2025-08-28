"""
Shared test fixtures and configuration for the job matching application tests.
"""
import pytest
import logging
from job_matching_app.services.ai_matching_service import AIMatchingService, OllamaConnectionError


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def ollama_availability():
    """
    Session-scoped fixture that checks Ollama service availability once per test session.
    
    Returns:
        dict: Contains 'available' (bool) and 'error_message' (str) keys
    """
    try:
        # Try to initialize AI service to test Ollama availability
        service = AIMatchingService()
        if service.is_ollama_available():
            logger.info("Ollama service is available for testing")
            return {
                'available': True,
                'error_message': None
            }
        else:
            error_msg = "Ollama service initialized but reports unavailable"
            logger.warning(error_msg)
            return {
                'available': False,
                'error_message': error_msg
            }
    except OllamaConnectionError as e:
        error_msg = f"Ollama connection failed: {str(e)}"
        logger.warning(error_msg)
        return {
            'available': False,
            'error_message': error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error checking Ollama availability: {str(e)}"
        logger.error(error_msg)
        return {
            'available': False,
            'error_message': error_msg
        }


@pytest.fixture
def require_ollama(ollama_availability):
    """
    Fixture that skips tests if Ollama is not available.
    
    Use this fixture in tests that require Ollama to be running.
    
    Args:
        ollama_availability: Session-scoped fixture with Ollama availability info
        
    Raises:
        pytest.skip: If Ollama service is not available
    """
    if not ollama_availability['available']:
        pytest.skip(
            f"Ollama service is required but not available: {ollama_availability['error_message']}\n"
            f"Please ensure:\n"
            f"1. Ollama is installed and running\n"
            f"2. At least one model is downloaded (e.g., 'ollama pull llama2')\n"
            f"3. Ollama service is accessible on the configured URL\n"
            f"4. No firewall is blocking the connection"
        )


@pytest.fixture
def ai_service_with_ollama_check():
    """
    Fixture that provides an AIMatchingService instance with Ollama availability check.
    
    Returns:
        AIMatchingService: Service instance if Ollama is available
        
    Raises:
        pytest.skip: If Ollama service is not available
    """
    try:
        service = AIMatchingService()
        if not service.is_ollama_available():
            pytest.skip(
                "Ollama service is not available for testing.\n"
                "Please ensure Ollama is running and properly configured."
            )
        return service
    except OllamaConnectionError as e:
        pytest.skip(
            f"Failed to connect to Ollama service: {str(e)}\n"
            f"Please ensure:\n"
            f"1. Ollama is installed and running ('ollama serve')\n"
            f"2. At least one model is downloaded (e.g., 'ollama pull llama2')\n"
            f"3. Ollama service is accessible on the configured URL"
        )
    except Exception as e:
        pytest.skip(f"Unexpected error initializing AI service: {str(e)}")


def pytest_configure(config):
    """
    Configure pytest with custom markers for Ollama-related tests.
    """
    config.addinivalue_line(
        "markers", 
        "requires_ollama: mark test as requiring Ollama service to be available"
    )


def pytest_collection_modifyitems(config, items):
    """
    Automatically add requires_ollama marker to tests that use Ollama fixtures.
    """
    ollama_fixtures = {'require_ollama', 'ai_service_with_ollama_check'}
    
    for item in items:
        # Check if test uses any Ollama-related fixtures
        if hasattr(item, 'fixturenames'):
            if any(fixture in ollama_fixtures for fixture in item.fixturenames):
                item.add_marker(pytest.mark.requires_ollama)


def pytest_runtest_setup(item):
    """
    Setup hook that runs before each test to provide clear error messages.
    """
    # Check if test is marked as requiring Ollama
    if item.get_closest_marker("requires_ollama"):
        # This will be handled by the require_ollama fixture
        pass


def pytest_report_header(config):
    """
    Add Ollama availability information to pytest report header.
    """
    try:
        service = AIMatchingService()
        if service.is_ollama_available():
            model_info = service.get_model_info()
            return [
                f"Ollama Status: Available",
                f"Ollama Model: {model_info.get('model', 'unknown')}",
                f"Model Size: {model_info.get('size', 'unknown')}"
            ]
        else:
            return ["Ollama Status: Service initialized but unavailable"]
    except OllamaConnectionError as e:
        return [
            f"Ollama Status: Connection failed - {str(e)}",
            "Note: Tests requiring Ollama will be skipped"
        ]
    except Exception as e:
        return [
            f"Ollama Status: Error checking availability - {str(e)}",
            "Note: Tests requiring Ollama may fail or be skipped"
        ]