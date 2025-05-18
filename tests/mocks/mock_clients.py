
# Mock simple para clientes externos

class MockVertexAIClient:
    # Cliente mock para Vertex AI
    
    def __init__(self, settings=None):
        self.settings = settings
        self._initialized = False
    
    async def initialize(self):
        # Inicializar el cliente
        self._initialized = True
        return True
    
    async def generate_content(self, prompt, temperature=0.7, max_tokens=1024):
        # Generar contenido
        return {
            "text": f"Respuesta simulada para: {prompt[:30]}...",
            "finish_reason": "STOP",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            },
            "model": "gemini-1.0-pro"
        }
    
    async def generate_embedding(self, text):
        # Generar embedding
        return [0.1] * 768  # Vector de 768 dimensiones
    
    async def process_multimodal(self, prompt, image_data, temperature=0.7):
        # Procesar contenido multimodal
        return {
            "text": f"Respuesta multimodal simulada para: {prompt[:30]}...",
            "finish_reason": "STOP",
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 30,
                "total_tokens": 50
            },
            "model": "gemini-1.0-pro-vision"
        }
    
    async def get_stats(self):
        # Obtener estadísticas
        return {
            "content_requests": 1,
            "embedding_requests": 1,
            "multimodal_requests": 0,
            "initialized": self._initialized
        }
