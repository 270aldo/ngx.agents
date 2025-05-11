import asyncio
import time
import logging # Mantendré logging estándar por ahora

from core.logging_config import get_logger

logger = get_logger(__name__)

# Intentar importar bibliotecas de Vertex AI
try:
    import google.auth
    import vertexai
    from vertexai.generative_models import GenerativeModel
    from vertexai.language_models import TextEmbeddingModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    logger.warning("No se pudieron importar las bibliotecas de Vertex AI para ConnectionPool. Usando modo mock.")
    VERTEX_AI_AVAILABLE = False

class ConnectionPool:
    """
    Pool de conexiones para Vertex AI.
    
    Gestiona un conjunto de conexiones reutilizables para mejorar el rendimiento
    y reducir el tiempo de inicialización.
    """
    
    def __init__(self, max_size=10, init_size=2, ttl=300, project=None, location="us-central1"):
        """
        Inicializa el pool de conexiones.
        
        Args:
            max_size: Tamaño máximo del pool
            init_size: Número inicial de conexiones a crear
            ttl: Tiempo de vida de las conexiones (segundos)
            project: Google Cloud Project ID. Si None, se infiere con google.auth.default().
            location: Google Cloud Location para Vertex AI.
        """
        self.max_size = max_size
        self.init_size = min(init_size, max_size) # init_size no puede ser mayor que max_size
        self.ttl = ttl
        self.project_id = project
        self.location = location
        
        # Lista de {client, timestamp, in_use}
        self.pool = []
        
        # Semáforo para limitar el número de conexiones activas (no necesariamente creadas)
        self.semaphore = asyncio.Semaphore(max_size)
        
        # Lock para operaciones críticas del pool
        self.lock = asyncio.Lock()
        
        # Stats
        self.stats = {
            "created": 0,
            "reused": 0,
            "acquired": 0,
            "released": 0,
            "expired": 0,
            "errors_creating": 0,
            "current_in_use": 0,
            "current_available_in_pool": 0,
            "max_concurrent_acquired": 0, # Máximo de clientes adquiridos simultáneamente
        }
        
        # Inicialización del pool
        self.initialized = False
        self._initializing_lock = asyncio.Lock() # Para evitar inicializaciones concurrentes

    async def _get_project_id(self):
        if self.project_id:
            return self.project_id
        if VERTEX_AI_AVAILABLE:
            try:
                _, project_id = google.auth.default()
                self.project_id = project_id
                return project_id
            except Exception as e:
                logger.error(f"No se pudo obtener project_id automáticamente: {e}")
                return None
        return None

    async def initialize(self):
        """Inicializa el pool con un número de conexiones iniciales."""
        if self.initialized:
            return
        
        async with self._initializing_lock: # Prevenir inicialización múltiple
            if self.initialized: # Doble check
                return
                
            logger.info(f"Inicializando pool de conexiones Vertex AI con hasta {self.init_size} conexiones.")
            # Obtener project_id si no está seteado
            if not self.project_id:
                await self._get_project_id()

            # Solo inicializar si Vertex AI está disponible y tenemos project_id
            if VERTEX_AI_AVAILABLE and self.project_id:
                try:
                    vertexai.init(project=self.project_id, location=self.location)
                    logger.info(f"Vertex AI SDK inicializado para proyecto {self.project_id} y locación {self.location}")
                except Exception as e:
                    logger.error(f"Error al inicializar Vertex AI SDK: {e}. El pool podría no funcionar.")

            created_count = 0
            for _ in range(self.init_size):
                if created_count >= self.init_size:
                    break
                try:
                    client = await self._create_new_client()
                    if not client.get("mock"): 
                        self.pool.append({
                            "client": client,
                            "timestamp": time.time(),
                            "in_use": False
                        })
                        self.stats["created"] += 1
                        created_count +=1
                    else:
                        self.stats["errors_creating"] +=1
                        if not VERTEX_AI_AVAILABLE: 
                            logger.warning("Vertex AI no disponible, deteniendo inicialización del pool.")
                            break
                except Exception as e:
                    logger.error(f"Error creando cliente durante inicialización: {e}")
                    self.stats["errors_creating"] +=1
            
            self.stats["current_available_in_pool"] = len(self.pool)
            self.initialized = True
            logger.info(f"Pool de {len(self.pool)}/{self.init_size} conexiones Vertex AI inicializado.")
    
    async def _create_new_client(self):
        """
        Crea un nuevo "cliente" de Vertex AI.
        """
        if not VERTEX_AI_AVAILABLE:
            return {"mock": True, "reason": "Vertex AI SDK no importado"}
        
        if not self.project_id:
            await self._get_project_id()
            if not self.project_id:
                 return {"mock": True, "reason": "Project ID no disponible", "error": "No se pudo obtener Google Cloud Project ID"}

        try:
            text_model = GenerativeModel("gemini-1.5-pro-latest")
            embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@latest")
            multimodal_model = GenerativeModel("gemini-1.5-pro-vision-latest")
            
            logger.info(f"Nuevo cliente Vertex AI creado para {self.project_id}")
            return {
                "text_model": text_model,
                "embedding_model": embedding_model,
                "multimodal_model": multimodal_model,
                "project_id": self.project_id,
                "location": self.location,
                "mock": False
            }
        except Exception as e:
            logger.error(f"Error al crear modelos de Vertex AI: {e}")
            self.stats["errors_creating"] += 1
            return {"mock": True, "error": str(e), "reason": "Error creando modelos"}
    
    async def acquire(self):
        """
        Adquiere un cliente del pool.
        """
        if not self.initialized: 
            await self.initialize()

        await self.semaphore.acquire()
        
        self.stats["acquired"] += 1
        self.stats["current_in_use"] = (self.max_size - self.semaphore._value)
        self.stats["max_concurrent_acquired"] = max(
            self.stats["max_concurrent_acquired"], self.stats["current_in_use"]
        )

        async with self.lock: 
            for entry in self.pool:
                if not entry["in_use"]:
                    if time.time() - entry["timestamp"] > self.ttl:
                        logger.info(f"Cliente en pool expirado. Creando nuevo. (TTL: {self.ttl}s)")
                        try:
                            entry["client"] = await self._create_new_client()
                            entry["timestamp"] = time.time()
                            self.stats["expired"] += 1
                            if not entry["client"].get("mock"):
                                self.stats["created"] += 1
                            else: 
                                self.semaphore.release()
                                self.stats["acquired"] -=1 
                                self.stats["current_in_use"] = (self.max_size - self.semaphore._value)
                                return entry["client"]
                        except Exception as e:
                            logger.error(f"Error reemplazando cliente expirado: {e}")
                            self.semaphore.release()
                            self.stats["acquired"] -=1
                            self.stats["current_in_use"] = (self.max_size - self.semaphore._value)
                            raise 
                    
                    if not entry["client"].get("mock"): 
                        entry["in_use"] = True
                        self.stats["reused"] += 1
                        self.stats["current_available_in_pool"] = len([e for e in self.pool if not e["in_use"]])
                        return entry["client"]
                    else: 
                        self.semaphore.release()
                        self.stats["acquired"] -=1
                        self.stats["current_in_use"] = (self.max_size - self.semaphore._value)
                        return entry["client"]
            
            if len(self.pool) < self.max_size:
                try:
                    new_client_obj = await self._create_new_client()
                    if not new_client_obj.get("mock"):
                        entry = {
                            "client": new_client_obj,
                            "timestamp": time.time(),
                            "in_use": True
                        }
                        self.pool.append(entry)
                        self.stats["created"] += 1
                        self.stats["current_available_in_pool"] = len([e for e in self.pool if not e["in_use"]])
                        return new_client_obj
                    else: 
                        self.semaphore.release()
                        self.stats["acquired"] -=1
                        self.stats["current_in_use"] = (self.max_size - self.semaphore._value)
                        return new_client_obj 
                except Exception as e:
                    logger.error(f"Error crítico creando nuevo cliente bajo demanda: {e}")
                    self.semaphore.release()
                    self.stats["acquired"] -=1
                    self.stats["current_in_use"] = (self.max_size - self.semaphore._value)
                    raise
            else:
                logger.error("Pool lleno y semáforo permitió adquirir, situación inesperada. Liberando semáforo.")
                self.semaphore.release()
                self.stats["acquired"] -=1
                self.stats["current_in_use"] = (self.max_size - self.semaphore._value)
                return {"mock": True, "error": "Pool Lleno Inesperadamente", "reason": "Situación de carrera potencial"}

    async def release(self, client_obj_to_release):
        """
        Libera un cliente de vuelta al pool.
        """
        released_from_pool = False
        async with self.lock: 
            for entry in self.pool:
                if id(entry["client"]) == id(client_obj_to_release):
                    if entry["in_use"]: 
                        entry["in_use"] = False
                        entry["timestamp"] = time.time()
                        self.stats["released"] += 1
                        released_from_pool = True
                    else:
                        pass 
                    break 
            
        if released_from_pool:
            self.semaphore.release()
            self.stats["current_in_use"] = (self.max_size - self.semaphore._value) 
            self.stats["current_available_in_pool"] = len([e for e in self.pool if not e["in_use"]])

    async def close(self):
        """Cierra todas las conexiones del pool (si aplica, para clientes con método close)."""
        logger.info("Cerrando pool de conexiones Vertex AI...")
        async with self.lock:
            self.pool = []
            self.initialized = False
            while self.semaphore.locked(): 
                try:
                    self.semaphore.release()
                except ValueError: 
                    break

            logger.info("Pool de conexiones Vertex AI cerrado y limpio.")
            self.stats["current_available_in_pool"] = 0
            self.stats["current_in_use"] = 0

    async def get_stats(self):
        async with self.lock: 
             self.stats["current_available_in_pool"] = len([e for e in self.pool if not e["in_use"]])
        return self.stats.copy()