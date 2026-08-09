"""LLM 客户端包:真实客户端(OpenAI 兼容) + Mock 客户端(离线演示)。"""

from .client import LLMClient, LLMError, encode_image_to_data_uri, parse_json
from .mock_client import MockLLMClient

__all__ = ["LLMClient", "LLMError", "MockLLMClient", "encode_image_to_data_uri", "parse_json"]
