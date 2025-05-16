"""
Sistema de presupuestos para agentes NGX.

Este módulo proporciona funcionalidades para gestionar presupuestos de tokens
por agente, permitiendo establecer límites, rastrear el uso y tomar acciones
cuando se alcanzan los límites.
"""

import logging
import time
import os
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, timedelta
import asyncio
import json
from enum import Enum
from pydantic import BaseModel, Field

from core.settings import settings

# Configurar logger
logger = logging.getLogger(__name__)

class BudgetPeriod(str, Enum):
    """Períodos para los presupuestos de tokens."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    INFINITE = "infinite"  # Sin reset, presupuesto total

class BudgetAction(str, Enum):
    """Acciones a tomar cuando se alcanza el límite de presupuesto."""
    BLOCK = "block"  # Bloquear completamente las llamadas
    DEGRADE = "degrade"  # Cambiar a un modelo más económico
    WARN = "warn"  # Solo advertir pero permitir la llamada
    QUEUE = "queue"  # Poner en cola para procesamiento posterior

class TokenUsage(BaseModel):
    """Modelo para el uso de tokens."""
    prompt_tokens: int = Field(default=0, description="Tokens utilizados en prompts")
    completion_tokens: int = Field(default=0, description="Tokens utilizados en completions")
    total_tokens: int = Field(default=0, description="Total de tokens utilizados")
    estimated_cost_usd: float = Field(default=0.0, description="Costo estimado en USD")

class AgentBudget(BaseModel):
    """Configuración de presupuesto para un agente."""
    agent_id: str = Field(..., description="ID del agente")
    max_tokens: int = Field(..., description="Máximo de tokens permitidos en el período")
    period: BudgetPeriod = Field(default=BudgetPeriod.MONTHLY, description="Período del presupuesto")
    action_on_limit: BudgetAction = Field(default=BudgetAction.WARN, description="Acción al alcanzar el límite")
    fallback_model: Optional[str] = Field(default=None, description="Modelo alternativo para modo degradado")
    reset_day: Optional[int] = Field(default=1, description="Día del mes/semana para reset (1-31 o 1-7)")
    
    class Config:
        use_enum_values = True

class BudgetManager:
    """
    Gestor de presupuestos para agentes NGX.
    
    Esta clase proporciona funcionalidades para gestionar presupuestos de tokens
    por agente, permitiendo establecer límites, rastrear el uso y tomar acciones
    cuando se alcanzan los límites.
    """
    
    # Instancia única (patrón Singleton)
    _instance = None
    
    def __new__(cls, *args: Any, **kwargs: Any) -> "BudgetManager":
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(BudgetManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, persistence_client=None):
        """
        Inicializa el gestor de presupuestos.
        
        Args:
            persistence_client: Cliente para persistencia de datos (opcional)
        """
        # Evitar reinicialización en el patrón Singleton
        if getattr(self, "_initialized", False):
            return
            
        self.persistence_client = persistence_client
        self.budgets: Dict[str, AgentBudget] = {}
        self.usage: Dict[str, Dict[str, TokenUsage]] = {}  # agent_id -> {period_key -> usage}
        self.last_reset: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self._initialized = True
        
        # Cargar configuraciones de presupuesto
        self._load_budgets()
        
        logger.info("BudgetManager inicializado")
    
    def _load_budgets(self) -> None:
        """Carga las configuraciones de presupuesto desde el archivo de configuración."""
        if not settings.enable_budgets:
            logger.info("Sistema de presupuestos deshabilitado en la configuración")
            return
            
        if not settings.budget_config_path:
            logger.warning("Ruta de configuración de presupuestos no especificada")
            return
            
        config_path = settings.budget_config_path
        if not os.path.exists(config_path):
            logger.warning(f"Archivo de configuración de presupuestos no encontrado: {config_path}")
            return
            
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Cargar configuración por defecto
            default_config = config.get('default', {})
            
            # Cargar configuraciones por agente
            agents_config = config.get('agents', {})
            
            for agent_id, agent_config in agents_config.items():
                # Combinar con valores por defecto
                merged_config = default_config.copy()
                merged_config.update(agent_config)
                
                # Crear objeto AgentBudget
                budget = AgentBudget(
                    agent_id=agent_id,
                    max_tokens=merged_config.get('max_tokens', 1000000),
                    period=merged_config.get('period', 'monthly'),
                    action_on_limit=merged_config.get('action_on_limit', settings.default_budget_action),
                    fallback_model=merged_config.get('fallback_model'),
                    reset_day=merged_config.get('reset_day', 1)
                )
                
                # Establecer presupuesto
                self.set_budget(budget)
                
            logger.info(f"Cargados presupuestos para {len(agents_config)} agentes")
            
        except Exception as e:
            logger.error(f"Error al cargar configuración de presupuestos: {e}")
    
    def set_budget(self, budget: AgentBudget) -> None:
        """
        Establece o actualiza el presupuesto para un agente.
        
        Args:
            budget: Configuración de presupuesto
        """
        self.budgets[budget.agent_id] = budget
        logger.info(f"Presupuesto establecido para agente {budget.agent_id}: {budget.max_tokens} tokens/{budget.period}")
    
    def get_budget(self, agent_id: str) -> Optional[AgentBudget]:
        """
        Obtiene la configuración de presupuesto para un agente.
        
        Args:
            agent_id: ID del agente
            
        Returns:
            Configuración de presupuesto o None si no existe
        """
        return self.budgets.get(agent_id)
    
    def _get_period_key(self, agent_id: str) -> str:
        """
        Obtiene la clave del período actual para un agente.
        
        Args:
            agent_id: ID del agente
            
        Returns:
            Clave del período (ej: "2025-05")
        """
        budget = self.get_budget(agent_id)
        if not budget:
            return "default"
            
        now = datetime.now()
        
        if budget.period == BudgetPeriod.DAILY:
            return now.strftime("%Y-%m-%d")
        elif budget.period == BudgetPeriod.WEEKLY:
            # Usar el número de semana ISO
            return f"{now.year}-W{now.isocalendar()[1]}"
        elif budget.period == BudgetPeriod.MONTHLY:
            return now.strftime("%Y-%m")
        elif budget.period == BudgetPeriod.YEARLY:
            return str(now.year)
        else:  # INFINITE
            return "infinite"
    
    def _should_reset(self, agent_id: str) -> bool:
        """
        Determina si se debe resetear el contador de tokens para un agente.
        
        Args:
            agent_id: ID del agente
            
        Returns:
            True si se debe resetear, False en caso contrario
        """
        budget = self.get_budget(agent_id)
        if not budget or budget.period == BudgetPeriod.INFINITE:
            return False
            
        now = datetime.now()
        last_reset = self.last_reset.get(agent_id)
        
        if not last_reset:
            return True
            
        if budget.period == BudgetPeriod.DAILY:
            return now.date() > last_reset.date()
        elif budget.period == BudgetPeriod.WEEKLY:
            # Resetear en el día de la semana especificado (1=lunes, 7=domingo)
            reset_day = budget.reset_day or 1
            current_weekday = now.weekday() + 1  # 1-7 (lunes-domingo)
            return current_weekday == reset_day and (now - last_reset).days >= 1
        elif budget.period == BudgetPeriod.MONTHLY:
            # Resetear en el día del mes especificado
            reset_day = min(budget.reset_day or 1, 28)  # Usar 28 como máximo para compatibilidad con febrero
            return now.day == reset_day and (now.year > last_reset.year or now.month > last_reset.month)
        elif budget.period == BudgetPeriod.YEARLY:
            # Resetear el 1 de enero
            return now.month == 1 and now.day == 1 and now.year > last_reset.year
            
        return False
    
    def _reset_usage(self, agent_id: str) -> None:
        """
        Resetea el contador de uso para un agente.
        
        Args:
            agent_id: ID del agente
        """
        period_key = self._get_period_key(agent_id)
        if agent_id in self.usage:
            # Archivar el uso anterior antes de resetear
            if self.persistence_client:
                try:
                    self.persistence_client.save_token_usage(
                        agent_id=agent_id,
                        period=period_key,
                        usage=self.usage[agent_id].get(period_key, TokenUsage())
                    )
                except Exception as e:
                    logger.error(f"Error al archivar uso de tokens para {agent_id}: {e}")
            
            # Crear nuevo período
            if period_key in self.usage[agent_id]:
                del self.usage[agent_id][period_key]
        
        self.last_reset[agent_id] = datetime.now()
        logger.info(f"Uso de tokens reseteado para agente {agent_id}")
    
    async def record_usage(self, 
                          agent_id: str, 
                          prompt_tokens: int, 
                          completion_tokens: int, 
                          model: str) -> Tuple[bool, Optional[str]]:
        """
        Registra el uso de tokens para un agente y verifica si se ha excedido el presupuesto.
        
        Args:
            agent_id: ID del agente
            prompt_tokens: Número de tokens en el prompt
            completion_tokens: Número de tokens en la respuesta
            model: Nombre del modelo utilizado
            
        Returns:
            Tupla (allowed, fallback_model) donde:
            - allowed: True si la operación está permitida, False si se ha excedido el presupuesto
            - fallback_model: Modelo alternativo si se debe degradar, None en caso contrario
        """
        async with self._lock:
            # Verificar si existe un presupuesto para este agente
            budget = self.get_budget(agent_id)
            if not budget:
                # Si no hay presupuesto definido, permitir la operación
                return True, None
            
            # Verificar si se debe resetear el contador
            if self._should_reset(agent_id):
                self._reset_usage(agent_id)
            
            # Obtener el período actual
            period_key = self._get_period_key(agent_id)
            
            # Inicializar estructura si no existe
            if agent_id not in self.usage:
                self.usage[agent_id] = {}
            if period_key not in self.usage[agent_id]:
                self.usage[agent_id][period_key] = TokenUsage()
            
            # Calcular costo estimado
            cost = self._estimate_cost(prompt_tokens, completion_tokens, model)
            
            # Actualizar uso
            usage = self.usage[agent_id][period_key]
            usage.prompt_tokens += prompt_tokens
            usage.completion_tokens += completion_tokens
            usage.total_tokens += (prompt_tokens + completion_tokens)
            usage.estimated_cost_usd += cost
            
            # Verificar si se ha excedido el presupuesto
            if usage.total_tokens > budget.max_tokens:
                logger.warning(
                    f"Presupuesto excedido para agente {agent_id}: "
                    f"{usage.total_tokens}/{budget.max_tokens} tokens"
                )
                
                # Determinar acción según la configuración
                if budget.action_on_limit == BudgetAction.BLOCK:
                    return False, None
                elif budget.action_on_limit == BudgetAction.DEGRADE and budget.fallback_model:
                    return True, budget.fallback_model
                elif budget.action_on_limit == BudgetAction.WARN:
                    return True, None
                elif budget.action_on_limit == BudgetAction.QUEUE:
                    # TODO: Implementar sistema de cola
                    return False, None
            
            return True, None
    
    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """
        Estima el costo en USD de una operación.
        
        Args:
            prompt_tokens: Número de tokens en el prompt
            completion_tokens: Número de tokens en la respuesta
            model: Nombre del modelo utilizado
            
        Returns:
            Costo estimado en USD
        """
        # Precios aproximados por 1000 tokens (actualizar según cambios de precios)
        model_prices = {
            # Gemini
            "gemini-1.5-pro": {"prompt": 0.00025, "completion": 0.00075},
            "gemini-1.5-flash": {"prompt": 0.00010, "completion": 0.00030},
            "gemini-1.0-pro": {"prompt": 0.00025, "completion": 0.00075},
            # GPT-4
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-4o": {"prompt": 0.005, "completion": 0.015},
            # GPT-3.5
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            # Claude
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
        }
        
        # Modelo por defecto si no se encuentra
        default_price = {"prompt": 0.001, "completion": 0.002}
        
        # Obtener precios para el modelo
        price = model_prices.get(model, default_price)
        
        # Calcular costo
        prompt_cost = (prompt_tokens / 1000) * price["prompt"]
        completion_cost = (completion_tokens / 1000) * price["completion"]
        
        return prompt_cost + completion_cost
    
    def get_usage(self, agent_id: str) -> Optional[TokenUsage]:
        """
        Obtiene el uso actual de tokens para un agente.
        
        Args:
            agent_id: ID del agente
            
        Returns:
            Uso de tokens o None si no hay datos
        """
        if agent_id not in self.usage:
            return None
            
        period_key = self._get_period_key(agent_id)
        return self.usage[agent_id].get(period_key)
    
    def get_all_usage(self) -> Dict[str, Dict[str, TokenUsage]]:
        """
        Obtiene el uso de tokens para todos los agentes.
        
        Returns:
            Diccionario con el uso de tokens por agente y período
        """
        return self.usage.copy()
    
    def get_budget_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado del presupuesto para un agente.
        
        Args:
            agent_id: ID del agente
            
        Returns:
            Diccionario con el estado del presupuesto
        """
        budget = self.get_budget(agent_id)
        usage = self.get_usage(agent_id)
        
        if not budget:
            return {"status": "no_budget", "agent_id": agent_id}
            
        if not usage:
            usage = TokenUsage()
            
        percentage = (usage.total_tokens / budget.max_tokens) * 100 if budget.max_tokens > 0 else 0
        
        return {
            "agent_id": agent_id,
            "budget": budget.dict(),
            "usage": usage.dict(),
            "percentage": percentage,
            "remaining": max(0, budget.max_tokens - usage.total_tokens),
            "period": self._get_period_key(agent_id),
            "next_reset": self._get_next_reset_date(agent_id)
        }
    
    def _get_next_reset_date(self, agent_id: str) -> Optional[datetime]:
        """
        Calcula la próxima fecha de reset para un agente.
        
        Args:
            agent_id: ID del agente
            
        Returns:
            Fecha del próximo reset o None si no aplica
        """
        budget = self.get_budget(agent_id)
        if not budget or budget.period == BudgetPeriod.INFINITE:
            return None
            
        now = datetime.now()
        
        if budget.period == BudgetPeriod.DAILY:
            # Próximo día a las 00:00
            return datetime(now.year, now.month, now.day) + timedelta(days=1)
        elif budget.period == BudgetPeriod.WEEKLY:
            # Próximo día de reset de la semana
            reset_day = budget.reset_day or 1  # 1-7 (lunes-domingo)
            current_weekday = now.weekday() + 1  # 1-7 (lunes-domingo)
            days_until_reset = (reset_day - current_weekday) % 7
            if days_until_reset == 0 and now.hour > 0:
                days_until_reset = 7
            return datetime(now.year, now.month, now.day) + timedelta(days=days_until_reset)
        elif budget.period == BudgetPeriod.MONTHLY:
            # Próximo día de reset del mes
            reset_day = min(budget.reset_day or 1, 28)
            if now.day < reset_day:
                # Mismo mes
                try:
                    return datetime(now.year, now.month, reset_day)
                except ValueError:
                    # Si el día no es válido para este mes (ej. 31 en febrero)
                    return datetime(now.year, now.month + 1, 1)
            else:
                # Próximo mes
                if now.month == 12:
                    return datetime(now.year + 1, 1, reset_day)
                else:
                    try:
                        return datetime(now.year, now.month + 1, reset_day)
                    except ValueError:
                        # Si el día no es válido para el próximo mes
                        return datetime(now.year, now.month + 2, 1)
        elif budget.period == BudgetPeriod.YEARLY:
            # Próximo 1 de enero
            if now.month == 12 and now.day == 31:
                return datetime(now.year + 1, 1, 1)
            else:
                return datetime(now.year + 1, 1, 1)
                
        return None

# Instancia global para uso en toda la aplicación
budget_manager = BudgetManager()