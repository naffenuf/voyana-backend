"""
AI service for managing prompts and calling various AI providers (OpenAI, Grok, etc.).
"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from flask import current_app
from openai import OpenAI
from app import db
from app.models.ai_trace import AITrace

logger = logging.getLogger(__name__)


class AIService:
    """Unified service for AI provider interactions with automatic trace logging."""

    def __init__(self):
        """Initialize AI service with API clients."""
        self.openai_client = None
        self._prompts = None  # Lazy loaded

    def _load_prompts(self) -> Dict[str, Any]:
        """Load prompts from prompts.json file (lazy loaded)."""
        if self._prompts is not None:
            return self._prompts

        # Use current_app if available, otherwise use relative path
        try:
            prompts_path = Path(current_app.root_path) / 'config' / 'prompts.json'
        except RuntimeError:
            # Not in app context, use relative path from this file
            prompts_path = Path(__file__).parent.parent / 'config' / 'prompts.json'

        try:
            with open(prompts_path, 'r') as f:
                self._prompts = json.load(f)
                return self._prompts
        except Exception as e:
            logger.error(f'Error loading prompts.json: {e}')
            return {}

    @property
    def prompts(self) -> Dict[str, Any]:
        """Get prompts (lazy loaded)."""
        return self._load_prompts()

    def _get_openai_client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if not self.openai_client:
            api_key = current_app.config.get('OPENAI_API_KEY')
            if not api_key:
                raise ValueError('OPENAI_API_KEY not configured')
            self.openai_client = OpenAI(api_key=api_key)
        return self.openai_client

    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """Replace {variable} placeholders in template with actual values."""
        result = template
        for key, value in variables.items():
            placeholder = f'{{{key}}}'
            result = result.replace(placeholder, str(value))
        return result

    def _create_trace(self, prompt_name: str, provider: str, model: str,
                     system_prompt: str, user_prompt: str, user_id: Optional[int] = None) -> AITrace:
        """Create a new AI trace record."""
        trace = AITrace(
            prompt_name=prompt_name,
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            status='pending',
            user_id=user_id
        )
        db.session.add(trace)
        db.session.commit()
        return trace

    def _update_trace_success(self, trace: AITrace, response: str, raw_request: Dict,
                             raw_response: Dict, metadata: Dict):
        """Update trace with successful response."""
        trace.response = response
        trace.raw_request = raw_request
        trace.raw_response = raw_response
        trace.trace_metadata = metadata
        trace.status = 'success'
        trace.completed_at = datetime.utcnow()
        db.session.commit()

    def _update_trace_error(self, trace: AITrace, error_message: str, raw_request: Dict = None):
        """Update trace with error information."""
        trace.error_message = error_message
        trace.status = 'error'
        trace.completed_at = datetime.utcnow()
        if raw_request:
            trace.raw_request = raw_request
        db.session.commit()

    def _call_openai(self, prompt_config: Dict[str, Any], system_prompt: str,
                    user_prompt: str, trace: AITrace) -> str:
        """Call OpenAI API."""
        try:
            client = self._get_openai_client()

            # Prepare request
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            # Extract parameters
            model = prompt_config.get('model', 'gpt-4o')
            temperature = prompt_config.get('temperature', 0.7)
            max_tokens = prompt_config.get('max_tokens', 500)

            raw_request = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            # Call API
            start_time = time.time()
            response = client.chat.completions.create(**raw_request)
            latency = time.time() - start_time

            # Extract response content
            content = response.choices[0].message.content

            # Prepare metadata
            metadata = {
                "latency": round(latency, 3),
                "tokens_prompt": response.usage.prompt_tokens,
                "tokens_completion": response.usage.completion_tokens,
                "tokens_total": response.usage.total_tokens,
                "finish_reason": response.choices[0].finish_reason
            }

            # Update trace
            raw_response = response.model_dump()
            self._update_trace_success(trace, content, raw_request, raw_response, metadata)

            return content

        except Exception as e:
            error_msg = f'OpenAI API error: {str(e)}'
            logger.error(error_msg)
            self._update_trace_error(trace, error_msg, raw_request)
            raise

    def _call_grok(self, prompt_config: Dict[str, Any], system_prompt: str,
                  user_prompt: str, trace: AITrace) -> str:
        """Call Grok (X.AI) API."""
        try:
            api_key = current_app.config.get('GROK_API_KEY')
            if not api_key:
                raise ValueError('GROK_API_KEY not configured')

            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            # Extract parameters
            parameters = prompt_config.get('parameters', {})
            model = prompt_config.get('model', 'grok-beta')

            # Build request payload
            payload = {
                "messages": messages,
                "model": model,
                "stream": False,
                "temperature": parameters.get('temperature', 0.7)
            }

            # Add max_tokens if specified
            if 'max_tokens' in parameters:
                payload['max_tokens'] = parameters['max_tokens']

            # Add response_format if specified (for JSON mode)
            if 'response_format' in parameters:
                payload['response_format'] = parameters['response_format']

            raw_request = payload.copy()

            # Call X.AI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            start_time = time.time()
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            latency = time.time() - start_time

            response.raise_for_status()
            response_data = response.json()

            # Extract content
            content = response_data['choices'][0]['message']['content']

            # Prepare metadata
            usage = response_data.get('usage', {})
            metadata = {
                "latency": round(latency, 3),
                "tokens_prompt": usage.get('prompt_tokens', 0),
                "tokens_completion": usage.get('completion_tokens', 0),
                "tokens_total": usage.get('total_tokens', 0),
                "finish_reason": response_data['choices'][0].get('finish_reason')
            }

            # Update trace
            self._update_trace_success(trace, content, raw_request, response_data, metadata)

            return content

        except requests.exceptions.RequestException as e:
            error_msg = f'Grok API error: {str(e)}'
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f' - {error_detail}'
                except:
                    error_msg += f' - {e.response.text}'
            logger.error(error_msg)
            self._update_trace_error(trace, error_msg, raw_request if 'raw_request' in locals() else None)
            raise
        except Exception as e:
            error_msg = f'Grok API error: {str(e)}'
            logger.error(error_msg)
            self._update_trace_error(trace, error_msg, raw_request if 'raw_request' in locals() else None)
            raise

    def execute_prompt(self, prompt_name: str, variables: Dict[str, Any],
                      user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute an AI prompt with variable substitution and automatic trace logging.

        Args:
            prompt_name: Name of the prompt in prompts.json
            variables: Dictionary of variables to substitute in the prompt template
            user_id: Optional user ID for trace tracking

        Returns:
            Dictionary with 'response' (AI response text), 'trace_id' (UUID), and 'parsed' (if JSON)

        Raises:
            ValueError: If prompt_name not found or required variables missing
            Exception: If API call fails
        """
        # Load prompt configuration
        if prompt_name not in self.prompts:
            raise ValueError(f'Prompt "{prompt_name}" not found in prompts.json')

        prompt_config = self.prompts[prompt_name]

        # Determine provider (default to openai for backward compatibility)
        provider = prompt_config.get('provider', 'openai')
        model = prompt_config.get('model', 'gpt-4o')

        # Render prompts
        system_prompt = prompt_config.get('system_prompt', '')
        user_prompt_template = prompt_config.get('user_prompt_template', '')

        system_prompt_rendered = self._render_template(system_prompt, variables)
        user_prompt_rendered = self._render_template(user_prompt_template, variables)

        # Create trace
        trace = self._create_trace(
            prompt_name=prompt_name,
            provider=provider,
            model=model,
            system_prompt=system_prompt_rendered,
            user_prompt=user_prompt_rendered,
            user_id=user_id
        )

        # Call appropriate provider
        try:
            if provider == 'openai':
                content = self._call_openai(prompt_config, system_prompt_rendered,
                                           user_prompt_rendered, trace)
            elif provider == 'grok':
                content = self._call_grok(prompt_config, system_prompt_rendered,
                                         user_prompt_rendered, trace)
            else:
                raise ValueError(f'Unsupported provider: {provider}')

            result = {
                'response': content,
                'trace_id': str(trace.id)
            }

            # Try to parse JSON if response_format is json_object
            parameters = prompt_config.get('parameters', {})
            response_format = parameters.get('response_format', {})
            if response_format.get('type') == 'json_object':
                try:
                    result['parsed'] = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f'Failed to parse JSON response for prompt {prompt_name}')

            return result

        except Exception as e:
            # Error already logged in provider-specific method
            raise


# Create a singleton instance
ai_service = AIService()
