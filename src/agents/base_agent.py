from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logger import get_logger
from src.llm.groq_client import GroqClient
from src.analyzers.pipeline import FileAnalysis, FunctionAnalysis

logger = get_logger(__name__)

class AgentType(Enum):
    """Types of specialized agents."""
    CODE_ANALYZER = "code_analyzer"
    SECURITY = "security"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    TEST = "test"
    STYLE = "style"

class MessageType(Enum):
    """Types of agent messages."""
    ANALYSIS = "analysis"
    SUGGESTION = "suggestion"
    ISSUE = "issue"
    QUESTION = "question"
    RESPONSE = "response"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    sender: AgentType
    recipient: Optional[AgentType]
    message_type: MessageType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = more important

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sender": self.sender.value,
            "recipient": self.recipient.value if self.recipient else None,
            "message_type": self.message_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "priority": self.priority
        }

@dataclass
class AgentSuggestion:
    """A suggestion from an agent."""
    agent_type: AgentType
    suggestion_type: str  # e.g., "refactor", "security_fix", "add_test"
    title: str
    description: str
    code_snippet: Optional[str] = None
    line_number: Optional[int] = None
    severity: str = "medium"  # low, medium, high, critical
    confidence: float = 0.8  # 0.0 to 1.0
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_type": self.agent_type.value,
            "suggestion_type": self.suggestion_type,
            "title": self.title,
            "description": self.description,
            "code_snippet": self.code_snippet,
            "line_number": self.line_number,
            "severity": self.severity,
            "confidence": self.confidence,
            "rationale": self.rationale
        }

@dataclass
class AgentState:
    """State maintained by an agent during execution."""
    agent_type: AgentType
    messages: List[AgentMessage] = field(default_factory=list)
    suggestions: List[AgentSuggestion] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    completed: bool = False
    error: Optional[str] = None

    def add_message(self, message: AgentMessage):
        """Add a message to the state."""
        self.messages.append(message)

    def add_suggestion(self, suggestion: AgentSuggestion):
        """Add a suggestion to the state."""
        self.suggestions.append(suggestion)

    def set_completed(self, completed: bool = True):
        """Set the completed status."""
        self.completed = completed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_type": self.agent_type.value,
            "messages": [msg.to_dict() for msg in self.messages],
            "suggestions": [sug.to_dict() for sug in self.suggestions],
            "context": self.context,
            "completed": self.completed,
            "error": self.error
        }

class BaseAgent(ABC):
    """
    Abstract base class for all code review agents.
    
    Each agent specializes in one aspect of code review:
    - Code quality and structure
    - Security vulnerabilities
    - Performance optimization
    - Documentation quality
    - Test coverage
    - Code style
    """
    def __init__(
        self,
        agent_type: AgentType,
        llm_client: GroqClient,
        model: str = "llama-3.1-8b-instant",
        max_tokens: int = 2048,
        temperature: float = 0.6,
    ):
        self.agent_type = agent_type
        self.llm_client = llm_client
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        self.state = AgentState(agent_type=agent_type)

        logger.info(f"Agent {self.agent_type.value} initialized")

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Defines the agent's role and expertise.
        
        Returns:
            System prompt string
        """
        pass
    
    @abstractmethod
    def analyze(self, file_analysis: FileAnalysis, context: Optional[Dict[str, Any]] = None) -> AgentState:
        """Analyze code and generate suggestions."""
        pass
  
    async def call_llm(self, user_prompt: str, system_prompt: Optional[str] = None, ) -> str:
        """
        Call LLM with prompt.
        """
        if system_prompt is None:
            system_prompt = self.get_system_prompt()    

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await self.llm_client.generate(
                messages=messages,
                model=self.model,
                max_tokens=self.max_tokens,
                stream=False,
            )

            content = response["choices"][0]["message"]["content"]
            
            return content
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return ""
    
    async def call_llm_stream(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None
    ):
        """
        Call LLM with streaming (ASYNC generator).
        
        Args:
            user_prompt: User/analysis prompt
            system_prompt: Optional system prompt override
        
        Yields:
            Streamed chunks of response
        """
        if system_prompt is None:
            system_prompt = self.get_system_prompt()
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            async for chunk in self.llm_client.generate_stream(
                messages=messages,
                model=self.model,
                max_tokens=self.max_tokens
            ):
                yield chunk
        
        except Exception as e:
            logger.error(f"LLM streaming failed for {self.agent_type.value}: {e}")
            raise
    def parse_llm_response(self, response: str) -> List[AgentSuggestion]:
        """
        Parse LLM response and extract suggestions.
        
        Args:
            response: Raw LLM response string
        
        Returns:
            List of AgentSuggestion objects
        """
        suggestions = []

        sections = response.split("\n\n")
        for section in sections:
            if not section.strip():
                continue

            lines = section.strip().split("\n")

            # Look for patterns like "Suggestion:", "Issue:", etc.
            if any(keyword in lines[0].lower() for keyword in ['suggestion', 'issue', 'recommendation']):
                suggestion = AgentSuggestion(
                    agent_type=self.agent_type,
                    suggestion_type="general",
                    title=lines[0],
                    description="\n".join(lines[1:]) if len(lines) > 1 else lines[0],
                    severity="medium",
                    confidence=0.7
                )
                suggestions.append(suggestion)
        
        return suggestions
    def send_message(
        self,
        recipient: Optional[AgentType],
        message_type: MessageType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ):
        """
        Send a message to another agent or broadcast.
        
        Args:
            recipient: Recipient agent (None for broadcast)
            message_type: Type of message
            content: Message content
            metadata: Additional metadata
            priority: Message priority
        """
        message = AgentMessage(
            sender=self.agent_type,
            recipient=recipient,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            priority=priority
        )
        
        self.state.add_message(message)
        logger.debug(
            f"{self.agent_type.value} sent {message_type.value} message "
            f"to {recipient.value if recipient else 'ALL'}"
        )
    
    def receive_messages(
        self,
        messages: List[AgentMessage]
    ) -> List[AgentMessage]:
        """
        Receive and filter messages for this agent.
        
        Args:
            messages: All messages from other agents
        
        Returns:
            Messages relevant to this agent
        """
        # Filter messages addressed to this agent or broadcast
        relevant_messages = [
            msg for msg in messages
            if msg.recipient is None or msg.recipient == self.agent_type
        ]
        
        # Add to state
        for msg in relevant_messages:
            self.state.add_message(msg)
        
        return relevant_messages
    
    def get_context_from_messages(
        self,
        messages: List[AgentMessage]
    ) -> Dict[str, Any]:
        """
        Extract relevant context from messages.
        
        Args:
            messages: Messages from other agents
        
        Returns:
            Context dictionary
        """
        context = {
            'other_agent_findings': [],
            'security_concerns': [],
            'complexity_issues': []
        }
        
        for msg in messages:
            if msg.message_type == MessageType.ISSUE:
                context['other_agent_findings'].append({
                    'agent': msg.sender.value,
                    'issue': msg.content
                })
            
            # Extract specific concerns
            if 'security' in msg.content.lower():
                context['security_concerns'].append(msg.content)
            
            if 'complex' in msg.content.lower():
                context['complexity_issues'].append(msg.content)
        
        return context
    
    def reset_state(self):
        """Reset agent state."""
        self.state = AgentState(agent_type=self.agent_type)
        logger.debug(f"{self.agent_type.value} state reset")
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.agent_type.value}>"