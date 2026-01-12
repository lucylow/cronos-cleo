"""
Rules and Decision Engine - Rule-based decision making for workflows
"""
import logging
from typing import Dict, List, Optional, Any
import re

from .models import Rule, DecisionTable

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Rule evaluation engine for workflow decisions.
    Supports rule-based decisions and decision tables.
    """
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.decision_tables: Dict[str, DecisionTable] = {}
    
    def register_rule(self, rule: Rule):
        """Register a rule"""
        self.rules[rule.rule_id] = rule
        logger.info(f"Registered rule: {rule.rule_id} ({rule.name})")
    
    def register_decision_table(self, table: DecisionTable):
        """Register a decision table"""
        self.decision_tables[table.table_id] = table
        logger.info(f"Registered decision table: {table.table_id} ({table.name})")
    
    async def evaluate_decision_table(
        self,
        table_id: str,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Evaluate a decision table and return the action
        
        Args:
            table_id: ID of decision table
            context: Context data for evaluation
        
        Returns:
            Action string or None
        """
        table = self.decision_tables.get(table_id)
        if not table:
            logger.warning(f"Decision table {table_id} not found")
            return table.default_action if table else None
        
        # Sort rules by priority (higher first)
        sorted_rules = sorted(table.rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            if not rule.enabled:
                continue
            
            if await self._evaluate_condition(rule.condition, context):
                logger.info(f"Decision table {table_id}: Rule {rule.rule_id} matched, action: {rule.action}")
                return rule.action
        
        # No rule matched, return default action
        return table.default_action
    
    async def evaluate_rule(self, rule_id: str, context: Dict[str, Any]) -> bool:
        """Evaluate a single rule"""
        rule = self.rules.get(rule_id)
        if not rule or not rule.enabled:
            return False
        
        return await self._evaluate_condition(rule.condition, context)
    
    async def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a condition expression
        
        Supports:
        - Simple comparisons: amount > 1000, status == "pending"
        - Logical operators: AND, OR, NOT
        - Variable access: input.amount, output.result
        - Function calls: contains(list, item)
        """
        try:
            # Simple expression evaluator (enhance with proper expression engine in production)
            # This is a simplified implementation - in production, use a proper expression engine
            # like simpleeval, jsonpath-rw, or a custom evaluator
            
            # Replace variables with their values
            expr = self._substitute_variables(condition, context)
            
            # Evaluate the expression (simplified - would use safe eval)
            # For production, use a proper expression evaluator
            return self._safe_eval(expr, context)
            
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    def _substitute_variables(self, expr: str, context: Dict[str, Any]) -> str:
        """Substitute variables in expression with their values"""
        # Simple variable substitution (enhance with proper expression engine)
        # Pattern: ${path.to.value} or $path.to.value
        def replace_var(match):
            var_path = match.group(1)
            try:
                value = self._get_nested_value(context, var_path.split('.'))
                return str(value)
            except:
                return match.group(0)
        
        # Replace ${variable} and $variable patterns
        expr = re.sub(r'\$\{([^}]+)\}', replace_var, expr)
        expr = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_.]*)', replace_var, expr)
        
        return expr
    
    def _get_nested_value(self, data: Dict[str, Any], path: List[str]) -> Any:
        """Get nested value from dictionary using path"""
        value = data
        for key in path:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                value = value[int(key)]
            else:
                raise KeyError(f"Path {'/'.join(path)} not found")
        return value
    
    def _safe_eval(self, expr: str, context: Dict[str, Any]) -> bool:
        """
        Safely evaluate a boolean expression
        
        WARNING: This is a simplified implementation.
        In production, use a proper expression evaluator library that:
        - Only allows safe operations
        - Prevents code injection
        - Supports the operations you need
        """
        # Simple boolean evaluation (enhance with proper expression engine)
        # For now, handle simple cases
        
        # Handle simple comparisons
        if '>' in expr:
            parts = expr.split('>', 1)
            try:
                left = self._eval_value(parts[0].strip(), context)
                right = self._eval_value(parts[1].strip(), context)
                return float(left) > float(right)
            except:
                pass
        
        if '<' in expr:
            parts = expr.split('<', 1)
            try:
                left = self._eval_value(parts[0].strip(), context)
                right = self._eval_value(parts[1].strip(), context)
                return float(left) < float(right)
            except:
                pass
        
        if '>=' in expr:
            parts = expr.split('>=', 1)
            try:
                left = self._eval_value(parts[0].strip(), context)
                right = self._eval_value(parts[1].strip(), context)
                return float(left) >= float(right)
            except:
                pass
        
        if '<=' in expr:
            parts = expr.split('<=', 1)
            try:
                left = self._eval_value(parts[0].strip(), context)
                right = self._eval_value(parts[1].strip(), context)
                return float(left) <= float(right)
            except:
                pass
        
        if '==' in expr:
            parts = expr.split('==', 1)
            try:
                left = self._eval_value(parts[0].strip(), context)
                right = self._eval_value(parts[1].strip(), context)
                return str(left) == str(right).strip('"\'')
            except:
                pass
        
        if '!=' in expr:
            parts = expr.split('!=', 1)
            try:
                left = self._eval_value(parts[0].strip(), context)
                right = self._eval_value(parts[1].strip(), context)
                return str(left) != str(right).strip('"\'')
            except:
                pass
        
        # Handle AND/OR
        if ' AND ' in expr.upper():
            parts = [p.strip() for p in expr.upper().split(' AND ')]
            return all(self._safe_eval(p, context) for p in parts)
        
        if ' OR ' in expr.upper():
            parts = [p.strip() for p in expr.upper().split(' OR ')]
            return any(self._safe_eval(p, context) for p in parts)
        
        # Boolean literals
        if expr.strip().upper() == 'TRUE':
            return True
        if expr.strip().upper() == 'FALSE':
            return False
        
        # Default: try to evaluate as boolean
        try:
            return bool(eval(expr))  # Simplified - use proper evaluator in production
        except:
            return False
    
    def _eval_value(self, value_str: str, context: Dict[str, Any]) -> Any:
        """Evaluate a value (number, string, variable)"""
        value_str = value_str.strip()
        
        # Try as number
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except:
            pass
        
        # Try as boolean
        if value_str.upper() == 'TRUE':
            return True
        if value_str.upper() == 'FALSE':
            return False
        
        # Try as variable
        if value_str.startswith('$'):
            var_path = value_str[1:].split('.')
            return self._get_nested_value(context, var_path)
        
        # Return as string (remove quotes)
        return value_str.strip('"\'')
    
    def create_risk_scoring_table(self) -> DecisionTable:
        """
        Create a risk scoring decision table for payment workflows
        
        Example decision table for risk assessment
        """
        rules = [
            Rule(
                rule_id="high_risk_amount",
                name="High Risk: Large Amount",
                condition="input.amount >= 1000000",  # 1M tokens
                action="flag_review",
                priority=100
            ),
            Rule(
                rule_id="medium_risk_amount",
                name="Medium Risk: Medium Amount",
                condition="input.amount >= 100000",  # 100k tokens
                action="add_score_30",
                priority=50
            ),
            Rule(
                rule_id="blacklist_country",
                name="High Risk: Blacklisted Country",
                condition="input.country IN ['XX', 'YY']",  # Example blacklist
                action="reject",
                priority=200
            ),
            Rule(
                rule_id="repeat_transaction",
                name="Medium Risk: Repeat Transaction",
                condition="input.tx_count_last_hour >= 5",
                action="add_score_50",
                priority=60
            ),
            Rule(
                rule_id="new_wallet",
                name="Low Risk: New Wallet",
                condition="input.wallet_age_days < 7",
                action="add_score_20",
                priority=30
            ),
        ]
        
        return DecisionTable(
            table_id="payment_risk_scoring",
            name="Payment Risk Scoring",
            rules=rules,
            default_action="approve"
        )

