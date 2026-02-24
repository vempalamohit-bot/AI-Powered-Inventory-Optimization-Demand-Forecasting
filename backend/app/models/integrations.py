"""Integration models for automated inventory sync"""

from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

class IntegrationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"

class SyncMethod(str, Enum):
    WEBHOOK = "webhook"  # Real-time push from external system
    SCHEDULED = "scheduled"  # Periodic pull/push
    API = "api"  # Direct API call
    CSV_UPLOAD = "csv_upload"  # Manual upload

class IntegrationConfig:
    """Configuration for external system integrations"""
    
    def __init__(
        self,
        name: str,
        system_type: str,  # "POS", "ERP", "Shopify", "Square", "Custom"
        sync_method: SyncMethod,
        api_key: str,
        webhook_url: Optional[str] = None,
        schedule: Optional[str] = None,  # cron expression: "0 8 * * *" = daily at 8am
        status: IntegrationStatus = IntegrationStatus.INACTIVE,
        last_sync: Optional[datetime] = None,
        sync_frequency_minutes: int = 60
    ):
        self.name = name
        self.system_type = system_type
        self.sync_method = sync_method
        self.api_key = api_key
        self.webhook_url = webhook_url
        self.schedule = schedule
        self.status = status
        self.last_sync = last_sync
        self.sync_frequency_minutes = sync_frequency_minutes

class InventoryUpdate:
    """Real-time inventory update from external system"""
    
    def __init__(
        self,
        sku: str,
        quantity_change: int,  # +10 for in, -5 for out
        reason: str,  # "sale", "restock", "adjustment", "return"
        source_system: str,  # Which system sent this
        timestamp: datetime = None
    ):
        self.sku = sku
        self.quantity_change = quantity_change
        self.reason = reason
        self.source_system = source_system
        self.timestamp = timestamp or datetime.utcnow()

class AuditLog:
    """Audit trail for inventory changes"""
    
    def __init__(
        self,
        product_id: int,
        action: str,  # "create", "update", "delete", "sync"
        old_value: Optional[Dict],
        new_value: Dict,
        source_system: str,  # Where the change came from
        user_id: Optional[str] = None,
        timestamp: datetime = None
    ):
        self.product_id = product_id
        self.action = action
        self.old_value = old_value
        self.new_value = new_value
        self.source_system = source_system
        self.user_id = user_id
        self.timestamp = timestamp or datetime.utcnow()
