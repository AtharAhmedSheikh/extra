from typing import List, Optional, Literal
from pydantic import BaseModel
from datetime import datetime


class TrackingEvent(BaseModel):
	status: Optional[str] = None
	activity_date: Optional[datetime | str] = None
	receiver_name: Optional[str] = None
	reason: Optional[str] = None
	location: Optional[str] = None
	details: Optional[str] = None


class TrackingResponse(BaseModel):
	# High-level result status for the provider call itself
	result: Literal["success", "failed", "pending"]

	# Carrier/courier identification and the queried tracking number
	courier: Optional[str] = None
	tracking_number: Optional[str] = None

	# Current shipment status summary
	current_status: Optional[str] = None

	# Parties and addressing (if available from provider)
	customer_name: Optional[str] = None
	customer_phone: Optional[str] = None
	delivery_address: Optional[str] = None
	merchant_name: Optional[str] = None

	# Shipment meta
	origin_city: Optional[str] = None
	destination_city: Optional[str] = None
	city_name: Optional[str] = None
	pickup_date: Optional[datetime | str] = None
	delivery_date: Optional[datetime | str] = None
	order_detail: Optional[str] = None
	order_id: Optional[str] = None

	# Event timeline
	events: List[TrackingEvent] = []

	# Error info (when result == "failed")
	error: Optional[str] = None
	provider_payload: Optional[dict] = None
