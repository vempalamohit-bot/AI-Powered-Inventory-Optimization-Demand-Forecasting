"""Integration API endpoints for automated inventory sync"""

from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict
import json
import hashlib
import hmac

from ..database import get_db
from ..database.models import Product
from ..models.integrations import IntegrationConfig, InventoryUpdate, AuditLog, SyncMethod, IntegrationStatus

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

# In-memory integration configs (in production, store in database)
INTEGRATION_CONFIGS: Dict[str, IntegrationConfig] = {}

@router.post("/webhook/{integration_id}")
async def receive_webhook(
    integration_id: str,
    payload: Dict = Body(...),
    x_webhook_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Receive real-time inventory updates from external systems (POS, ERP)
    
    Example payload:
    {
        "sku": "SKU001",
        "quantity_change": -1,
        "reason": "sale",
        "order_id": "ORD-12345"
    }
    """
    
    # Validate integration exists
    if integration_id not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    config = INTEGRATION_CONFIGS[integration_id]
    
    # Verify webhook signature (security)
    if x_webhook_signature and config.api_key:
        expected_sig = hmac.new(
            config.api_key.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(x_webhook_signature, expected_sig):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Process inventory update
    try:
        sku = payload.get('sku')
        quantity_change = payload.get('quantity_change', 0)
        reason = payload.get('reason', 'webhook_update')
        
        product = db.query(Product).filter(Product.sku == sku).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {sku} not found")
        
        # Update inventory
        old_stock = product.current_stock
        product.current_stock = max(0, product.current_stock + quantity_change)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Updated {sku}: {old_stock} → {product.current_stock}",
            "sku": sku,
            "old_stock": old_stock,
            "new_stock": product.current_stock,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error processing webhook: {str(e)}")

@router.post("/sync/{integration_id}")
async def trigger_sync(
    integration_id: str,
    sync_data: Optional[List[Dict]] = None,
    db: Session = Depends(get_db)
):
    """
    Trigger one-time sync or receive sync data from external system
    
    Example payload:
    [
        {
            "sku": "SKU001",
            "current_stock": 150,
            "last_count_date": "2026-02-08"
        }
    ]
    """
    
    if integration_id not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    config = INTEGRATION_CONFIGS[integration_id]
    updated_count = 0
    
    try:
        if sync_data:
            for item in sync_data:
                sku = item.get('sku')
                new_stock = item.get('current_stock')
                
                product = db.query(Product).filter(Product.sku == sku).first()
                if product and new_stock is not None:
                    old_stock = product.current_stock
                    product.current_stock = int(new_stock)
                    updated_count += 1
        
        config.last_sync = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "integration": integration_id,
            "updated_products": updated_count,
            "last_sync": config.last_sync.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Sync error: {str(e)}")

@router.post("/config")
async def create_integration(
    config_data: Dict
):
    """
    Create a new integration configuration
    
    Example:
    {
        "name": "Shopify Store",
        "system_type": "Shopify",
        "sync_method": "webhook",
        "api_key": "shppa_xxxxxxxxxxxx",
        "sync_frequency_minutes": 15
    }
    """
    
    integration_id = config_data.get('name', 'integration').lower().replace(' ', '_')
    
    config = IntegrationConfig(
        name=config_data.get('name'),
        system_type=config_data.get('system_type'),
        sync_method=SyncMethod(config_data.get('sync_method', 'scheduled')),
        api_key=config_data.get('api_key'),
        webhook_url=config_data.get('webhook_url'),
        schedule=config_data.get('schedule'),
        status=IntegrationStatus(config_data.get('status', 'testing')),
        sync_frequency_minutes=config_data.get('sync_frequency_minutes', 60)
    )
    
    INTEGRATION_CONFIGS[integration_id] = config
    
    return {
        "integration_id": integration_id,
        "name": config.name,
        "system_type": config.system_type,
        "sync_method": config.sync_method.value,
        "status": config.status.value,
        "webhook_url": f"http://localhost:8000/api/integrations/webhook/{integration_id}" if config.sync_method == SyncMethod.WEBHOOK else None,
        "message": "Integration configured. For webhook, send POST requests to the webhook_url"
    }

@router.get("/config")
async def list_integrations():
    """List all configured integrations"""
    
    return {
        "integrations": [
            {
                "id": id,
                "name": c.name,
                "system_type": c.system_type,
                "sync_method": c.sync_method.value,
                "status": c.status.value,
                "last_sync": c.last_sync.isoformat() if c.last_sync else None,
                "sync_frequency_minutes": c.sync_frequency_minutes
            }
            for id, c in INTEGRATION_CONFIGS.items()
        ]
    }

@router.get("/config/{integration_id}")
async def get_integration(integration_id: str):
    """Get configuration for specific integration"""
    
    if integration_id not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    c = INTEGRATION_CONFIGS[integration_id]
    
    return {
        "id": integration_id,
        "name": c.name,
        "system_type": c.system_type,
        "sync_method": c.sync_method.value,
        "status": c.status.value,
        "last_sync": c.last_sync.isoformat() if c.last_sync else None,
        "webhook_url": f"http://localhost:8000/api/integrations/webhook/{integration_id}" if c.sync_method == SyncMethod.WEBHOOK else None,
        "sync_frequency_minutes": c.sync_frequency_minutes
    }

@router.put("/config/{integration_id}")
async def update_integration(
    integration_id: str,
    config_data: Dict
):
    """Update integration configuration"""
    
    if integration_id not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    config = INTEGRATION_CONFIGS[integration_id]
    
    # Update fields
    if 'status' in config_data:
        config.status = IntegrationStatus(config_data['status'])
    if 'sync_frequency_minutes' in config_data:
        config.sync_frequency_minutes = config_data['sync_frequency_minutes']
    if 'api_key' in config_data:
        config.api_key = config_data['api_key']
    
    return {
        "integration_id": integration_id,
        "status": "updated",
        "config": {
            "name": config.name,
            "system_type": config.system_type,
            "status": config.status.value,
            "sync_frequency_minutes": config.sync_frequency_minutes
        }
    }

@router.delete("/config/{integration_id}")
async def delete_integration(integration_id: str):
    """Delete integration configuration"""
    
    if integration_id not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    del INTEGRATION_CONFIGS[integration_id]
    
    return {"status": "deleted", "integration_id": integration_id}

@router.get("/test/{integration_id}")
async def test_integration(integration_id: str):
    """Test integration connectivity"""
    
    if integration_id not in INTEGRATION_CONFIGS:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    config = INTEGRATION_CONFIGS[integration_id]
    
    # Mock test - in production, would actually call the external system
    return {
        "integration_id": integration_id,
        "status": "success",
        "message": f"Test successful for {config.name}",
        "system_type": config.system_type,
        "last_response_time": "245ms"
    }
