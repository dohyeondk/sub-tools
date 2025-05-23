import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, MagicMock

from sub_tools.intelligence.client import (
    audio_to_subtitles, 
    RateLimitExceededError, 
    AudioProcessingError,
    APIConnectionError,
    InvalidResponseError,
    TranscriptionError
)


@pytest_asyncio.fixture
async def mock_openai_client():
    with patch('sub_tools.intelligence.client.AsyncOpenAI') as mock_client:
        # Setup the mock client
        instance = MagicMock()
        mock_client.return_value = instance
        
        # Create a mock chat completions object
        chat_completions = MagicMock()
        instance.chat.completions.create = chat_completions
        
        yield {
            'client': mock_client,
            'instance': instance,
            'chat_completions': chat_completions
        }


@pytest.mark.asyncio
async def test_audio_to_subtitles_success(mock_openai_client, tmp_path):
    # Create a simple audio file
    audio_file = tmp_path / "test_audio.mp3"
    audio_file.write_bytes(b"test audio content")
    
    # Mock the API response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "1\n00:00:00,000 --> 00:00:05,000\nTest subtitles"
    mock_openai_client['chat_completions'].return_value = mock_response
    
    # Call the function
    result = await audio_to_subtitles("fake_api_key", "test_model", str(audio_file), "mp3", "English")
    
    # Verify results
    assert "Test subtitles" in result
    assert mock_openai_client['client'].called


@pytest.mark.asyncio
async def test_audio_to_subtitles_file_not_found(mock_openai_client):
    # Test with non-existent file
    with pytest.raises(AudioProcessingError) as exc_info:
        await audio_to_subtitles("fake_api_key", "test_model", "/nonexistent/file.mp3", "mp3", "English")
    
    assert "Failed to read audio file" in str(exc_info.value)


@pytest.mark.asyncio
async def test_audio_to_subtitles_rate_limit_error(mock_openai_client, tmp_path):
    # Create a simple audio file
    audio_file = tmp_path / "test_audio.mp3"
    audio_file.write_bytes(b"test audio content")
    
    # Mock rate limit error
    from openai import RateLimitError
    mock_openai_client['chat_completions'].side_effect = RateLimitError("Rate limit exceeded")
    
    # Call the function and expect exception
    with pytest.raises(RateLimitExceededError) as exc_info:
        await audio_to_subtitles("fake_api_key", "test_model", str(audio_file), "mp3", "English")
    
    assert "rate limit exceeded" in str(exc_info.value).lower()