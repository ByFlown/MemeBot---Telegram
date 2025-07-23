import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

class AILogLevel(Enum):
    """AI-specific log levels for different types of AI events"""
    DECISION = "DECISION"
    ANALYSIS = "ANALYSIS"
    PREDICTION = "PREDICTION"
    LEARNING = "LEARNING"
    ERROR = "ERROR"
    PERFORMANCE = "PERFORMANCE"

class AISystemLogger:
    """Specialized logger for AI system operations and decisions"""
    
    def __init__(self, name: str = "ai_system"):
        self.logger = logging.getLogger(f"ai.{name}")
        self.logger.setLevel(logging.INFO)
        
        # Create AI-specific formatter
        formatter = logging.Formatter(
            '%(asctime)s - 🤖 AI[%(name)s] - %(levelname)s - %(message)s'
        )
        
        # Only add handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _format_ai_message(self, log_level: AILogLevel, message: str, 
                          context: Optional[Dict[str, Any]] = None,
                          metrics: Optional[Dict[str, float]] = None) -> str:
        """Format AI log message with structured data"""
        
        parts = [f"[{log_level.value}] {message}"]
        
        if context:
            context_str = json.dumps(context, indent=None, separators=(',', ':'))
            parts.append(f"Context: {context_str}")
        
        if metrics:
            metrics_str = ", ".join([f"{k}={v:.4f}" for k, v in metrics.items()])
            parts.append(f"Metrics: {metrics_str}")
        
        return " | ".join(parts)
    
    def decision(self, message: str, decision_data: Optional[Dict] = None, 
                confidence: Optional[float] = None, reasoning: Optional[str] = None):
        """Log AI trading decisions"""
        context = {}
        metrics = {}
        
        if decision_data:
            context.update(decision_data)
        
        if confidence is not None:
            metrics['confidence'] = confidence
        
        if reasoning:
            context['reasoning'] = reasoning
        
        formatted_msg = self._format_ai_message(
            AILogLevel.DECISION, message, context, metrics
        )
        self.logger.info(formatted_msg)
    
    def analysis(self, message: str, token_address: Optional[str] = None,
                analysis_data: Optional[Dict] = None, scores: Optional[Dict[str, float]] = None):
        """Log AI analysis results"""
        context = {}
        metrics = {}
        
        if token_address:
            context['token'] = token_address[:8] + "..." + token_address[-8:] if len(token_address) > 16 else token_address
        
        if analysis_data:
            context.update(analysis_data)
        
        if scores:
            metrics.update(scores)
        
        formatted_msg = self._format_ai_message(
            AILogLevel.ANALYSIS, message, context, metrics
        )
        self.logger.info(formatted_msg)
    
    def prediction(self, message: str, predicted_value: Optional[float] = None,
                  prediction_horizon: Optional[str] = None, model_info: Optional[Dict] = None):
        """Log AI predictions"""
        context = {}
        metrics = {}
        
        if predicted_value is not None:
            metrics['predicted_value'] = predicted_value
        
        if prediction_horizon:
            context['horizon'] = prediction_horizon
        
        if model_info:
            context.update(model_info)
        
        formatted_msg = self._format_ai_message(
            AILogLevel.PREDICTION, message, context, metrics
        )
        self.logger.info(formatted_msg)
    
    def learning(self, message: str, episode: Optional[int] = None,
                reward: Optional[float] = None, loss: Optional[float] = None,
                learning_data: Optional[Dict] = None):
        """Log AI learning progress and training updates"""
        context = {}
        metrics = {}
        
        if episode is not None:
            context['episode'] = episode
        
        if reward is not None:
            metrics['reward'] = reward
        
        if loss is not None:
            metrics['loss'] = loss
        
        if learning_data:
            context.update(learning_data)
        
        formatted_msg = self._format_ai_message(
            AILogLevel.LEARNING, message, context, metrics
        )
        self.logger.info(formatted_msg)
    
    def performance(self, message: str, performance_metrics: Dict[str, float],
                   period: Optional[str] = None):
        """Log AI performance metrics"""
        context = {}
        
        if period:
            context['period'] = period
        
        formatted_msg = self._format_ai_message(
            AILogLevel.PERFORMANCE, message, context, performance_metrics
        )
        self.logger.info(formatted_msg)
    
    def error(self, message: str, error_details: Optional[Dict] = None,
             recovery_action: Optional[str] = None):
        """Log AI system errors"""
        context = {}
        
        if error_details:
            context.update(error_details)
        
        if recovery_action:
            context['recovery'] = recovery_action
        
        formatted_msg = self._format_ai_message(
            AILogLevel.ERROR, message, context
        )
        self.logger.error(formatted_msg)
    
    def model_update(self, model_name: str, update_type: str, 
                    performance_before: Optional[float] = None,
                    performance_after: Optional[float] = None,
                    update_details: Optional[Dict] = None):
        """Log model updates and improvements"""
        metrics = {}
        context = {'model': model_name, 'update_type': update_type}
        
        if performance_before is not None:
            metrics['performance_before'] = performance_before
        
        if performance_after is not None:
            metrics['performance_after'] = performance_after
            if performance_before is not None:
                metrics['improvement'] = performance_after - performance_before
        
        if update_details:
            context.update(update_details)
        
        message = f"Model updated: {model_name}"
        formatted_msg = self._format_ai_message(
            AILogLevel.LEARNING, message, context, metrics
        )
        self.logger.info(formatted_msg)
    
    def trade_execution(self, action: str, token_address: str, amount: float,
                       ai_confidence: float, reasoning: List[str],
                       expected_outcome: Optional[str] = None):
        """Log AI-driven trade executions"""
        context = {
            'action': action,
            'token': token_address[:8] + "..." + token_address[-8:],
            'amount': amount,
            'reasoning': reasoning,
        }
        
        if expected_outcome:
            context['expected_outcome'] = expected_outcome
        
        metrics = {'ai_confidence': ai_confidence}
        
        message = f"AI executing {action} trade"
        formatted_msg = self._format_ai_message(
            AILogLevel.DECISION, message, context, metrics
        )
        self.logger.info(formatted_msg)
    
    def scanning_decision(self, tokens_analyzed: int, tokens_accepted: int,
                         rejection_reasons: Dict[str, int],
                         analysis_duration: float):
        """Log AI scanning and filtering decisions"""
        metrics = {
            'tokens_analyzed': float(tokens_analyzed),
            'tokens_accepted': float(tokens_accepted),
            'acceptance_rate': float(tokens_accepted / tokens_analyzed) if tokens_analyzed > 0 else 0.0,
            'analysis_duration_sec': analysis_duration
        }
        
        context = {
            'rejection_reasons': rejection_reasons
        }
        
        message = f"Scanning completed: {tokens_accepted}/{tokens_analyzed} tokens accepted"
        formatted_msg = self._format_ai_message(
            AILogLevel.ANALYSIS, message, context, metrics
        )
        self.logger.info(formatted_msg)

# Create global AI logger instances for different components
ai_trader_logger = AISystemLogger('trader')
ai_scanner_logger = AISystemLogger('scanner')
ai_analyzer_logger = AISystemLogger('analyzer')
ai_model_logger = AISystemLogger('model')

# Convenience function to get component-specific logger
def get_ai_logger(component: str) -> AISystemLogger:
    """Get AI logger for specific component"""
    return AISystemLogger(component)