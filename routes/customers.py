from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel
from typing import List, Optional, Literal

from whatsapp_agent.database.customer import CustomerDataBase
from whatsapp_agent.schema.customer_schema import CustomerSchema

customer_router = APIRouter(prefix="/customers", tags=["Customers"])

class CustomerListResponse(BaseModel):
    customers: List[CustomerSchema]
    total: int

class CustomerUpdateRequest(BaseModel):
    customer_name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    company_name: Optional[str] = None
    tags: Optional[List[str]] = None

class CustomerSearchResponse(BaseModel):
    customers: List[CustomerSchema]
    total: int
    query: str

class HighValueCustomersResponse(BaseModel):
    customers: List[CustomerSchema]
    total: int
    min_spend_threshold: int

customer_db = CustomerDataBase()

@customer_router.get("/")
async def get_customers(
    limit: int = Query(50, ge=1, le=100, description="Number of customers to return"),
    customer_type: Optional[Literal["B2B", "D2C"]] = Query(None, description="Filter by customer type")
):
    """Get list of customers with optional filtering."""
    try:
        customers = customer_db.list_customers(limit=limit)
        
        if customer_type:
            customers = [c for c in customers if c.get("customer_type") == customer_type]
        
        return CustomerListResponse(
            customers=[CustomerSchema.model_validate(c) for c in customers],
            total=len(customers)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve customers: {str(e)}")

@customer_router.get("/{phone_number}")
async def get_customer(
    phone_number: str = Path(..., description="Customer phone number")
):
    """Get customer details by phone number."""
    try:
        customer = customer_db.get_customer_by_phone(phone_number)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve customer: {str(e)}")

@customer_router.put("/{phone_number}")
async def update_customer(
    phone_number: str = Path(..., description="Customer phone number"),
    updates: CustomerUpdateRequest = ...
):
    """Update customer information."""
    try:
        existing_customer = customer_db.get_customer_by_phone(phone_number)
        if not existing_customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid updates provided")
        
        result = customer_db.update_customer(phone_number, update_data)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update customer")
        
        return {"message": "Customer updated successfully", "updated_fields": list(update_data.keys())}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update customer: {str(e)}")

@customer_router.post("/{phone_number}/escalate")
async def escalate_customer(phone_number: str = Path(..., description="Customer phone number")):
    """Escalate customer to human support."""
    try:
        success = customer_db.update_escalation_status(phone_number, True)
        if not success:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"message": "Customer escalated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to escalate customer: {str(e)}")

@customer_router.post("/{phone_number}/de-escalate")
async def de_escalate_customer(phone_number: str = Path(..., description="Customer phone number")):
    """Remove escalation status from customer."""
    try:
        success = customer_db.update_escalation_status(phone_number, False)
        if not success:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"message": "Customer de-escalated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to de-escalate customer: {str(e)}")

@customer_router.get("/search")
async def search_customers(
    q: str = Query(..., description="Search query for customer name, phone, or company"),
    limit: int = Query(20, ge=1, le=100)
):
    """Search customers by name, phone number, or company."""
    try:
        customers = customer_db.list_customers(limit=1000)
        
        # Simple text search across relevant fields
        results = []
        for customer in customers:
            search_fields = [
                customer.get("customer_name", "").lower(),
                customer.get("phone_number", "").lower(),
                customer.get("company_name", "").lower(),
                customer.get("email", "").lower()
            ]
            
            if any(q.lower() in field for field in search_fields):
                results.append(customer)
        
        return {
            "customers": [CustomerSchema.model_validate(c) for c in results[:limit]],
            "total": len(results),
            "query": q
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@customer_router.get("/escalated")
async def get_escalated_customers(
    limit: int = Query(50, ge=1, le=100)
):
    """Get all escalated customers."""
    try:
        customers = customer_db.list_customers(limit=1000)
        escalated = [c for c in customers if c.get("escalation_status", False)]
        
        return {
            "customers": [CustomerSchema.model_validate(c) for c in escalated[:limit]],
            "total": len(escalated)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get escalated customers: {str(e)}")

@customer_router.get("/high-value")
async def get_high_value_customers(
    min_spend: int = Query(10000, description="Minimum spend threshold"),
    limit: int = Query(50, ge=1, le=100)
):
    """Get high-value customers based on spending."""
    try:
        customers = customer_db.list_customers(limit=1000)
        high_value = [c for c in customers if (c.get("total_spend", 0) or 0) >= min_spend]
        
        # Sort by spend descending
        high_value.sort(key=lambda x: x.get("total_spend", 0) or 0, reverse=True)
        
        return {
            "customers": [CustomerSchema.model_validate(c) for c in high_value[:limit]],
            "total": len(high_value),
            "min_spend_threshold": min_spend
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get high-value customers: {str(e)}")