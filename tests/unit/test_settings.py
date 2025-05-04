"""
Pruebas unitarias para la configuración de la aplicación.
"""
import pytest
from core.test_settings import MockTestSettings


def test_test_settings_initialization(monkeypatch):
    """Verifica que MockTestSettings se inicializa correctamente."""
    # Crear una instancia de MockTestSettings con valores explícitos
    settings = MockTestSettings(
        supabase_url="http://localhost:54321",
        supabase_anon_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
        jwt_secret="test_secret_key",
        testing=True
    )
    
    # Verificar valores por defecto
    assert str(settings.supabase_url).startswith("http://localhost:54321")
    assert settings.supabase_anon_key.startswith("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
    assert settings.jwt_secret == "test_secret_key"
    assert settings.testing is True
    
    # Verificar valores heredados de Settings
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.debug is False
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expiration_minutes == 60
    assert settings.env == "dev"
    assert settings.log_level == "INFO"
