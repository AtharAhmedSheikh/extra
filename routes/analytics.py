from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List

from whatsapp_agent.database.customer import CustomerDataBase
from whatsapp_agent.database.chat_history import ChatHistoryDataBase

analytics_router = APIRouter(prefix="/analytics",tags=["analytics"])

class CustomerStatsResponse(BaseModel):
    total_customers: int
    active_customers: int
    escalated_customers: int
    b2b_customers: int
    d2c_customers: int
    avg_total_spend: float

class MessageStatsResponse(BaseModel):
    total_conversations: int
    total_messages: int
    avg_messages_per_conversation: float
    message_types: Dict[str, int]

class AnalyticsOverviewResponse(BaseModel):
    customer_stats: CustomerStatsResponse
    message_stats: MessageStatsResponse
    top_customers_by_spend: List[Dict]

customer_db = CustomerDataBase()
chat_db = ChatHistoryDataBase()

@analytics_router.get("/overview")
async def get_analytics_overview():
    """Get comprehensive analytics overview."""
    try:
        # Customer analytics
        customers = customer_db.list_customers(limit=1000)
        
        total_customers = len(customers)
        active_customers = sum(1 for c in customers if c.get("is_active", False))
        escalated_customers = sum(1 for c in customers if c.get("escalation_status", False))
        b2b_customers = sum(1 for c in customers if c.get("customer_type") == "B2B")
        d2c_customers = sum(1 for c in customers if c.get("customer_type") == "D2C")
        
        total_spend = sum(c.get("total_spend", 0) or 0 for c in customers)
        avg_total_spend = total_spend / total_customers if total_customers > 0 else 0
        
        # Top customers by spend
        top_customers = sorted(
            [{"phone_number": c.get("phone_number"), "name": c.get("customer_name"), "spend": c.get("total_spend", 0) or 0} 
             for c in customers], 
            key=lambda x: x["spend"], reverse=True
        )[:5]
        
        customer_stats = CustomerStatsResponse(
            total_customers=total_customers,
            active_customers=active_customers,
            escalated_customers=escalated_customers,
            b2b_customers=b2b_customers,
            d2c_customers=d2c_customers,
            avg_total_spend=round(avg_total_spend, 2)
        )
        
        # Message analytics (simplified - would need proper chat history query)
        message_stats = MessageStatsResponse(
            total_conversations=total_customers,  # Approximation
            total_messages=0,  # Would need to count from chat history
            avg_messages_per_conversation=0.0,
            message_types={"text": 0, "image": 0, "voice": 0, "audio": 0}
        )
        
        return AnalyticsOverviewResponse(
            customer_stats=customer_stats,
            message_stats=message_stats,
            top_customers_by_spend=top_customers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate analytics: {str(e)}")

@analytics_router.get("/customers/stats")
async def get_customers_stats():
    """Get detailed customer statistics."""
    try:
        customers = customer_db.list_customers(limit=1000)
        
        stats = {
            "total": len(customers),
            "active": sum(1 for c in customers if c.get("is_active", False)),
            "inactive": sum(1 for c in customers if not c.get("is_active", False)),
            "escalated": sum(1 for c in customers if c.get("escalation_status", False)),
            "by_type": {
                "B2B": sum(1 for c in customers if c.get("customer_type") == "B2B"),
                "D2C": sum(1 for c in customers if c.get("customer_type") == "D2C")
            },
            "spend_analysis": {
                "total_spend": sum(c.get("total_spend", 0) or 0 for c in customers),
                "avg_spend": sum(c.get("total_spend", 0) or 0 for c in customers) / len(customers) if customers else 0,
                "high_value_customers": sum(1 for c in customers if (c.get("total_spend", 0) or 0) > 10000)
            }
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate customer stats: {str(e)}")

@analytics_router.get("/escalations")
async def get_escalation_stats():
    """Get escalation statistics."""
    try:
        customers = customer_db.list_customers(limit=1000)
        
        escalated = [c for c in customers if c.get("escalation_status", False)]
        
        stats = {
            "total_escalations": len(escalated),
            "escalation_rate": (len(escalated) / len(customers) * 100) if customers else 0,
            "escalated_by_type": {
                "B2B": sum(1 for c in escalated if c.get("customer_type") == "B2B"),
                "D2C": sum(1 for c in escalated if c.get("customer_type") == "D2C")
            },
            "escalated_customers": [
                {"phone_number": c.get("phone_number"), 
                 "customer_name": c.get("customer_name"),
                 "customer_type": c.get("customer_type"),
                 "total_spend": c.get("total_spend", 0) or 0}
                for c in escalated
            ]
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get escalation stats: {str(e)}")

@analytics_router.get("/messages/stats")
async def get_message_stats():
    """Get message analytics from chat history."""
    try:
        # Get all customers to iterate through their chats
        customers = customer_db.list_customers(limit=1000)
        
        total_conversations = 0
        total_messages = 0
        message_types = {"text": 0, "image": 0, "voice": 0, "audio": 0}
        
        for customer in customers:
            phone_number = customer.get("phone_number")
            messages = chat_db.get_recent_chat_history_by_phone(phone_number, limit=1000)
            
            if messages:
                total_conversations += 1
                total_messages += len(messages)
                
                for msg in messages:
                    msg_type = getattr(msg, 'message_type', 'text')
                    if msg_type in message_types:
                        message_types[msg_type] += 1
        
        avg_messages = total_messages / total_conversations if total_conversations > 0 else 0
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "avg_messages_per_conversation": round(avg_messages, 2),
            "message_types": message_types
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get message stats: {str(e)}")

@analytics_router.get("/dashboard")
async def get_dashboard_summary():
    """Get key metrics for dashboard."""
    try:
        customers = customer_db.list_customers(limit=1000)
        
        # Basic counts
        total_customers = len(customers)
        active_customers = sum(1 for c in customers if c.get("is_active", False))
        escalated_customers = sum(1 for c in customers if c.get("escalation_status", False))
        
        # Revenue metrics
        total_revenue = sum(c.get("total_spend", 0) or 0 for c in customers)
        avg_customer_value = total_revenue / total_customers if total_customers > 0 else 0
        
        # Customer type breakdown
        b2b_count = sum(1 for c in customers if c.get("customer_type") == "B2B")
        d2c_count = sum(1 for c in customers if c.get("customer_type") == "D2C")
        
        return {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "escalated_customers": escalated_customers,
            "total_revenue": total_revenue,
            "avg_customer_value": round(avg_customer_value, 2),
            "customer_breakdown": {
                "B2B": b2b_count,
                "D2C": d2c_count
            },
            "escalation_rate": round((escalated_customers / total_customers * 100), 2) if total_customers > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard summary: {str(e)}")