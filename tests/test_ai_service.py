"""
Tests for AI Service.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from app.services.ai_service import AIService, ai_service
from app.models.ai_trace import AITrace
from app import db


class TestAIServicePromptExecution:
    """Tests for AI service prompt execution."""

    @patch('app.services.ai_service.OpenAI')
    def test_execute_openai_prompt(self, mock_openai_class, app):
        """Test executing an OpenAI prompt."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='Test response'))]
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        with app.app_context():
            service = AIService()
            result = service.execute_prompt(
                'site_description_from_coordinates',
                {
                    'site_name': 'Test Site',
                    'latitude': '40.7589',
                    'longitude': '-73.9851'
                }
            )

            assert result is not None
            assert 'response' in result or isinstance(result, str)

    @patch('app.services.ai_service.OpenAI')
    def test_execute_prompt_creates_trace(self, mock_openai_class, app, test_user):
        """Test that executing a prompt creates an AI trace."""
        # Mock OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='Response'))]
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        with app.app_context():
            service = AIService()
            service.execute_prompt(
                'site_description_from_coordinates',
                {'site_name': 'Test', 'latitude': '40', 'longitude': '-73'},
                user_id=test_user.id
            )

            # Check that a trace was created
            traces = AITrace.query.filter_by(user_id=test_user.id).all()
            assert len(traces) >= 1

    @patch('app.services.ai_service.OpenAI')
    def test_execute_prompt_handles_api_error(self, mock_openai_class, app):
        """Test that API errors are handled gracefully."""
        # Mock API error
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception('API Error')
        mock_openai_class.return_value = mock_client

        with app.app_context():
            service = AIService()
            result = service.execute_prompt(
                'site_description_from_coordinates',
                {'site_name': 'Test', 'latitude': '40', 'longitude': '-73'}
            )

            # Should return None or error
            assert result is None or 'error' in str(result).lower()

    def test_execute_prompt_invalid_prompt_name(self, app):
        """Test executing with invalid prompt name."""
        with app.app_context():
            service = AIService()
            result = service.execute_prompt(
                'nonexistent_prompt',
                {'test': 'value'}
            )

            assert result is None or 'error' in str(result).lower()


class TestAIServiceTemplateRendering:
    """Tests for template variable substitution."""

    def test_render_template_simple(self, app):
        """Test simple variable substitution."""
        with app.app_context():
            service = AIService()
            template = "Hello {name}, you are {age} years old."
            variables = {'name': 'John', 'age': '25'}

            result = service._render_template(template, variables)

            assert result == "Hello John, you are 25 years old."

    def test_render_template_missing_variable(self, app):
        """Test template rendering with missing variables."""
        with app.app_context():
            service = AIService()
            template = "Hello {name}"
            variables = {}

            # Should handle missing variables gracefully
            result = service._render_template(template, variables)
            assert result is not None


class TestAdminAIEndpoints:
    """Tests for admin AI endpoints."""

    @patch('app.services.ai_service.OpenAI')
    def test_generate_description_endpoint(self, mock_openai_class, client, admin_headers):
        """Test the generate description admin endpoint."""
        # Mock OpenAI
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='Generated description'))]
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        response = client.post('/api/admin/ai/generate-description', headers=admin_headers, json={
            'siteName': 'Times Square',
            'latitude': 40.7580,
            'longitude': -73.9855
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'description' in data or 'response' in data

    def test_generate_description_requires_admin(self, client, auth_headers):
        """Test that generating descriptions requires admin role."""
        response = client.post('/api/admin/ai/generate-description', headers=auth_headers, json={
            'siteName': 'Test',
            'latitude': 40,
            'longitude': -73
        })

        assert response.status_code in [403, 401]

    def test_list_ai_traces(self, app, client, admin_headers, test_user):
        """Test listing AI traces."""
        with app.app_context():
            # Create some traces
            trace1 = AITrace(
                prompt_name='test_prompt',
                provider='openai',
                model='gpt-4',
                response='Test response',
                status='success',
                user_id=test_user.id
            )
            db.session.add(trace1)
            db.session.commit()

        response = client.get('/api/admin/ai/traces', headers=admin_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'traces' in data
        assert len(data['traces']) >= 1

    def test_list_traces_requires_admin(self, client, auth_headers):
        """Test that listing traces requires admin role."""
        response = client.get('/api/admin/ai/traces', headers=auth_headers)

        assert response.status_code in [403, 401]

    def test_get_specific_trace(self, app, client, admin_headers, test_user):
        """Test getting a specific AI trace."""
        with app.app_context():
            trace = AITrace(
                prompt_name='test_prompt',
                provider='openai',
                model='gpt-4',
                response='Test response',
                status='success',
                user_id=test_user.id
            )
            db.session.add(trace)
            db.session.commit()
            trace_id = trace.id

        response = client.get(f'/api/admin/ai/traces/{trace_id}', headers=admin_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        assert str(data['id']) == str(trace_id)

    def test_get_trace_stats(self, app, client, admin_headers, test_user):
        """Test getting AI trace statistics."""
        with app.app_context():
            # Create traces with different stats
            for i in range(5):
                trace = AITrace(
                    prompt_name=f'prompt_{i}',
                    provider='openai',
                    model='gpt-4',
                    response=f'Response {i}',
                    status='success',
                    user_id=test_user.id
                )
                db.session.add(trace)
            db.session.commit()

        response = client.get('/api/admin/ai/traces/stats', headers=admin_headers)

        assert response.status_code == 200
        data = json.loads(response.data)
        # Should have some statistics
        assert len(data) > 0


class TestAITraceModel:
    """Tests for AI Trace model."""

    def test_create_trace(self, app, test_user):
        """Test creating an AI trace."""
        with app.app_context():
            trace = AITrace(
                prompt_name='test_prompt',
                provider='openai',
                model='gpt-4o',
                system_prompt='System prompt',
                user_prompt='User prompt',
                response='AI response',
                status='success',
                user_id=test_user.id,
                trace_metadata={'tokens': 100, 'cost': 0.01}
            )
            db.session.add(trace)
            db.session.commit()

            # Verify it was saved
            saved_trace = AITrace.query.filter_by(prompt_name='test_prompt').first()
            assert saved_trace is not None
            assert saved_trace.provider == 'openai'
            assert saved_trace.status == 'success'

    def test_trace_to_dict(self, app, test_user):
        """Test AI trace serialization."""
        with app.app_context():
            trace = AITrace(
                prompt_name='test_prompt',
                provider='openai',
                model='gpt-4o',
                response='Test',
                status='success',
                user_id=test_user.id
            )
            db.session.add(trace)
            db.session.commit()

            trace_dict = trace.to_dict()
            assert 'id' in trace_dict
            assert trace_dict['promptName'] == 'test_prompt'
            assert trace_dict['provider'] == 'openai'
