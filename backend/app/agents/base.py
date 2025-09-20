"""
Base agent interface and protocol
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
from app.models.schemas import PRContext, AgentResult


@runtime_checkable
class BaseAgent(Protocol):
    """Protocol for PR analysis agents"""
    
    def run(self, ctx: PRContext) -> AgentResult:
        """
        Run agent analysis on PR context
        
        Args:
            ctx: PR context data
            
        Returns:
            Agent analysis result
        """
        ...


class AbstractAgent(ABC):
    """Abstract base class for agents"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def run(self, ctx: PRContext) -> AgentResult:
        """Run agent analysis"""
        pass
    
    def _create_result(self, payload: dict, warnings: list = None) -> AgentResult:
        """Helper to create agent result"""
        return AgentResult(
            name=self.name,
            payload=payload,
            warnings=warnings or []
        )