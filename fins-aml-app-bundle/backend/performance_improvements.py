"""
Performance and AI improvements for AML Backend
"""

import asyncio
import redis
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

# 1. CACHING LAYER
class CacheService:
    """Redis caching for expensive queries"""

    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

    async def get_cached_dashboard_data(self, dashboard_type: str, analyst: str = None) -> Optional[Dict]:
        """Cache dashboard data for 5 minutes"""
        cache_key = f"dashboard:{dashboard_type}:{analyst or 'all'}"
        cached_data = self.redis_client.get(cache_key)

        if cached_data:
            return json.loads(cached_data)
        return None

    async def cache_dashboard_data(self, dashboard_type: str, data: Dict, analyst: str = None):
        """Cache dashboard data with 5 minute TTL"""
        cache_key = f"dashboard:{dashboard_type}:{analyst or 'all'}"
        self.redis_client.setex(cache_key, 300, json.dumps(data))

# 2. SMART AI CONTEXT BUILDING
class ContextBuilder:
    """Build smarter context for AI assistant"""

    @staticmethod
    def build_investigation_context(alert_id: str, customer_data: Dict, transactions: List[Dict]) -> Dict:
        """Build rich context for AI assistant"""

        # Analyze transaction patterns
        pattern_analysis = ContextBuilder._analyze_transaction_patterns(transactions)

        # Get relevant regulatory context
        regulatory_context = ContextBuilder._get_regulatory_context(alert_id, pattern_analysis)

        # Build customer risk profile
        risk_profile = ContextBuilder._build_risk_profile(customer_data, transactions)

        return {
            "alert_context": {
                "alert_id": alert_id,
                "customer_summary": f"{customer_data.get('customer_name')} - {customer_data.get('occupation')}",
                "risk_indicators": risk_profile,
                "pattern_summary": pattern_analysis
            },
            "transaction_context": {
                "total_amount": sum(t['amount'] for t in transactions),
                "transaction_count": len(transactions),
                "time_span": f"{transactions[0]['transaction_date']} to {transactions[-1]['transaction_date']}",
                "channels_used": list(set(t.get('channel') for t in transactions)),
                "flagged_patterns": pattern_analysis['red_flags']
            },
            "regulatory_context": regulatory_context,
            "suggested_queries": [
                "What are the specific red flags for this transaction pattern?",
                "Does this activity match our structuring detection criteria?",
                "What documentation should I request from the customer?",
                "Should this be escalated to a SAR filing?"
            ]
        }

    @staticmethod
    def _analyze_transaction_patterns(transactions: List[Dict]) -> Dict:
        """Analyze transactions for suspicious patterns"""

        patterns = {
            "red_flags": [],
            "pattern_type": None,
            "severity": "low"
        }

        # Check for structuring (amounts just below $10K)
        below_threshold = [t for t in transactions if 9000 <= t['amount'] < 10000]
        if len(below_threshold) >= 3:
            patterns["red_flags"].append("Multiple deposits below CTR threshold")
            patterns["pattern_type"] = "structuring"
            patterns["severity"] = "high"

        # Check for rapid movement
        total_in = sum(t['amount'] for t in transactions if t['transaction_type'].endswith('_in'))
        total_out = sum(t['amount'] for t in transactions if t['transaction_type'].endswith('_out'))
        if total_out > total_in * 0.9:  # >90% moved out
            patterns["red_flags"].append("Rapid fund movement - high outflow ratio")
            patterns["pattern_type"] = "rapid_movement"

        # Check for round dollar amounts
        round_amounts = [t for t in transactions if t['amount'] % 1000 == 0]
        if len(round_amounts) / len(transactions) > 0.7:
            patterns["red_flags"].append("High frequency of round dollar amounts")

        return patterns

    @staticmethod
    def _get_regulatory_context(alert_id: str, pattern_analysis: Dict) -> Dict:
        """Get relevant regulatory guidance"""

        context = {
            "relevant_guidance": [],
            "filing_requirements": [],
            "red_flag_citations": []
        }

        if pattern_analysis["pattern_type"] == "structuring":
            context["relevant_guidance"].append("31 CFR 1020.320 - Currency Transaction Reports")
            context["filing_requirements"].append("SAR filing required if structuring is confirmed")
            context["red_flag_citations"].append("FFIEC BSA/AML Appendix F: Structuring indicators")

        return context

# 3. QUERY OPTIMIZATION
class QueryOptimizer:
    """Optimize database queries"""

    @staticmethod
    def build_optimized_alert_query(filters: Dict) -> str:
        """Build optimized query with proper indexing hints"""

        base_query = """
        SELECT
          a.alert_id,
          a.customer_id,
          c.customer_name,
          a.scenario_name,
          a.alert_score,
          a.priority,
          a.total_amount,
          a.alert_status,
          a.created_date
        FROM fins_aml.data_generation.alerts a
        JOIN fins_aml.data_generation.customers c ON a.customer_id = c.customer_id
        """

        # Add WHERE conditions in order of selectivity
        where_conditions = []

        # Most selective first
        if filters.get('alert_status'):
            where_conditions.append(f"a.alert_status = '{filters['alert_status']}'")

        if filters.get('priority'):
            where_conditions.append(f"a.priority = '{filters['priority']}'")

        if filters.get('analyst_name'):
            where_conditions.append(f"a.analyst_name = '{filters['analyst_name']}'")

        if filters.get('date_range'):
            where_conditions.append(f"a.created_date >= '{filters['date_range']['start']}'")
            where_conditions.append(f"a.created_date <= '{filters['date_range']['end']}'")

        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)

        # Order by priority, then creation date
        base_query += """
        ORDER BY
          CASE a.priority
            WHEN 'critical' THEN 1
            WHEN 'high' THEN 2
            WHEN 'medium' THEN 3
            ELSE 4
          END,
          a.created_date DESC
        LIMIT 50
        """

        return base_query

# 4. REAL-TIME NOTIFICATIONS
class NotificationService:
    """Real-time notifications for analysts"""

    async def check_for_new_critical_alerts(self) -> List[Dict]:
        """Check for new critical alerts every 30 seconds"""

        # Query for alerts created in last 30 seconds with critical priority
        query = """
        SELECT alert_id, customer_name, scenario_name, alert_score
        FROM fins_aml.data_generation.v_analyst_queue
        WHERE priority = 'critical'
        AND created_date >= CURRENT_TIMESTAMP - INTERVAL 30 SECONDS
        """

        # This would integrate with WebSockets to push to frontend
        return []

    async def check_sla_violations(self) -> List[Dict]:
        """Check for alerts approaching SLA deadline"""

        query = """
        SELECT alert_id, assigned_analyst, days_in_queue
        FROM fins_aml.data_generation.v_analyst_queue
        WHERE days_in_queue >= 4 -- 1 day before 5-day SLA
        AND alert_status IN ('new', 'assigned', 'in_progress')
        """

        return []

# 5. ENHANCED AI PROMPTING
class ImprovedPromptBuilder:
    """Build better prompts for MAS agent"""

    @staticmethod
    def build_investigation_prompt(context: Dict, user_question: str) -> str:
        """Build comprehensive prompt with full context"""

        prompt = f"""You are an expert AML investigator assistant analyzing a suspicious activity alert.

INVESTIGATION CONTEXT:
Alert ID: {context['alert_context']['alert_id']}
Customer: {context['alert_context']['customer_summary']}

TRANSACTION ANALYSIS:
- Total Amount: ${context['transaction_context']['total_amount']:,.2f}
- Transaction Count: {context['transaction_context']['transaction_count']}
- Time Period: {context['transaction_context']['time_span']}
- Channels: {', '.join(context['transaction_context']['channels_used'])}

IDENTIFIED RED FLAGS:
{chr(10).join('- ' + flag for flag in context['transaction_context']['flagged_patterns'])}

REGULATORY CONTEXT:
{chr(10).join('- ' + guidance for guidance in context['regulatory_context']['relevant_guidance'])}

ANALYST QUESTION: {user_question}

Please provide a detailed analysis that:
1. Directly answers the analyst's question
2. References specific regulatory guidance where applicable
3. Provides concrete next steps for the investigation
4. Highlights any additional red flags or concerns
5. Suggests specific documentation to request if needed

Be precise, professional, and actionable in your response."""

        return prompt