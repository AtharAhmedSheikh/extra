from agents import function_tool
from openai import BaseModel
from whatsapp_agent.quickbook.invoices import QuickBookInvoice
from whatsapp_agent._debug import Logger
from typing import List, Dict, Any, Optional

class InvoiceItems(BaseModel):
    quantity: int
    name: str

qb_invoice = QuickBookInvoice()

@function_tool(strict_mode=False)
def create_invoice_tool(customer_id: str, invoice_items: List[InvoiceItems]) -> Dict[str, Any]:
    """
    Create a new invoice for a specific customer.
    
    Args:
        customer_id: QuickBooks customer ID.
        invoice_items: List of dicts with {"name": str, "quantity": int}
    """
    Logger.info(f"Creating invoice for customer {customer_id} with items: {invoice_items}")
    return qb_invoice.create_invoice(customer_id, invoice_items)

@function_tool
def get_invoice_tool(invoice_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch details of a specific invoice.
    
    Args:
        invoice_id: The QuickBooks invoice ID.
    """
    Logger.info(f"Fetching invoice details for invoice ID: {invoice_id}")
    return qb_invoice.get_invoice(invoice_id)

@function_tool
def get_invoices_by_customer_tool(customer_id: str) -> List[Dict[str, Any]]:
    """
    Get all invoices for a specific customer.
    
    Args:
        customer_id: QuickBooks customer ID.
    """
    Logger.info(f"Fetching invoices for customer ID: {customer_id}")
    return qb_invoice.get_invoices_by_customer(customer_id)

@function_tool
def get_last_invoice_by_customer_tool(customer_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent invoice for a customer.
    
    Args:
        customer_id: QuickBooks customer ID.
    """
    Logger.info(f"Fetching last invoice for customer ID: {customer_id}")
    return qb_invoice.get_last_invoice_by_customer(customer_id)

@function_tool
def check_invoice_status_tool(invoice_id: str) -> Optional[str]:
    """
    Check if a specific invoice is Paid or Unpaid.
    
    Args:
        invoice_id: QuickBooks invoice ID.
    """
    Logger.info(f"Checking invoice status for invoice ID: {invoice_id}")
    return qb_invoice.check_invoice_status(invoice_id)

@function_tool
def get_unpaid_invoices_by_customer_tool(customer_id: str) -> List[Dict[str, Any]]:
    """
    Get all unpaid invoices for a specific customer.
    
    Args:
        customer_id: QuickBooks customer ID.
    """
    Logger.info(f"Fetching unpaid invoices for customer ID: {customer_id}")
    return qb_invoice.get_unpaid_invoices_by_customer(customer_id)

@function_tool
def get_due_date_tool(invoice_id: str) -> Optional[str]:
    """
    Get the due date of a specific invoice.
    
    Args:
        invoice_id: QuickBooks invoice ID.
    """
    Logger.info(f"Fetching due date for invoice ID: {invoice_id}")
    return qb_invoice.get_due_date(invoice_id)
