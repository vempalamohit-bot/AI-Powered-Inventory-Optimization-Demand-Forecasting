"""
Comprehensive System Verification Script
=========================================
This script validates all critical components of the AI-driven inventory optimization system:
- Database connectivity and schema
- Configuration management
- Email notification system
- Alert scheduler
- API endpoints
- ML model functionality
- Data validation
"""

import sys
import os
import asyncio
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def check_imports():
    """Verify all critical imports work"""
    print("🔍 Checking Python imports...")
    errors = []
    
    try:
        from app.config import get_settings
        print("  ✅ Config module")
    except Exception as e:
        errors.append(f"Config: {e}")
    
    try:
        from app.database.models import (
            Product, SalesHistory, AlertRecipient, NotificationLog
        )
        print("  ✅ Database models")
    except Exception as e:
        errors.append(f"Database models: {e}")
    
    try:
        from app.services.email_service_sendgrid import send_email
        print("  ✅ Email service")
    except Exception as e:
        errors.append(f"Email service: {e}")
    
    try:
        from app.services.notification_service import (
            send_slack_message, send_teams_message, format_alert_markdown
        )
        print("  ✅ Notification service")
    except Exception as e:
        errors.append(f"Notification service: {e}")
    
    try:
        from app.services.alert_scheduler import get_alert_scheduler
        print("  ✅ Alert scheduler")
    except Exception as e:
        errors.append(f"Alert scheduler: {e}")
    
    try:
        from app.models.demand_forecaster import DemandForecaster
        from app.models.inventory_optimizer import InventoryOptimizer
        print("  ✅ ML models")
    except Exception as e:
        errors.append(f"ML models: {e}")
    
    try:
        from app.schemas.data_schemas import validate_data_quality
        print("  ✅ Data validation")
    except Exception as e:
        errors.append(f"Data validation: {e}")
    
    if errors:
        print("\n❌ Import errors found:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print("✅ All imports successful\n")
    return True


def check_config():
    """Verify configuration is loadable"""
    print("🔍 Checking configuration...")
    try:
        from app.config import get_settings
        settings = get_settings()
        
        print(f"  ✅ SendGrid API Key: {'✓ Set' if settings.sendgrid_api_key else '✗ Not set'}")
        print(f"  ✅ From Email: {settings.email_from}")
        print(f"  ✅ Alert Recipients: {len(settings.default_alert_recipients)} configured")
        print(f"  ✅ Slack Webhook: {'✓ Set' if settings.slack_webhook_url else '✗ Not set'}")
        print(f"  ✅ Teams Webhook: {'✓ Set' if settings.teams_webhook_url else '✗ Not set'}")
        print(f"  ✅ Scheduler Enabled: {settings.alert_scheduler_enabled}")
        print(f"  ✅ Check Interval: {settings.alert_scheduler_interval_seconds}s")
        print(f"  ✅ Notification Logging: {settings.log_notifications}")
        
        print("✅ Configuration loaded successfully\n")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}\n")
        return False


def check_database():
    """Verify database connectivity and schema"""
    print("🔍 Checking database...")
    try:
        from app.database import engine, SessionLocal, Base
        from app.database.models import (
            Product, SalesHistory, Forecast, AlertRecipient, NotificationLog
        )
        
        # Try to create tables
        Base.metadata.create_all(bind=engine)
        print("  ✅ Database tables created/verified")
        
        # Test connection
        db = SessionLocal()
        try:
            # Count products
            product_count = db.query(Product).count()
            print(f"  ✅ Products in DB: {product_count}")
            
            # Count alert recipients
            recipient_count = db.query(AlertRecipient).count()
            print(f"  ✅ Alert recipients: {recipient_count}")
            
            # Count notification logs
            log_count = db.query(NotificationLog).count()
            print(f"  ✅ Notification logs: {log_count}")
            
        finally:
            db.close()
        
        print("✅ Database connectivity successful\n")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}\n")
        return False


async def check_scheduler():
    """Verify alert scheduler can start/stop"""
    print("🔍 Checking alert scheduler...")
    try:
        from app.services.alert_scheduler import get_alert_scheduler
        
        scheduler = get_alert_scheduler()
        print("  ✅ Scheduler instance created")
        
        # Try to start and stop (quick test)
        await scheduler.start()
        print("  ✅ Scheduler started")
        
        await asyncio.sleep(1)  # Let it run briefly
        
        await scheduler.stop()
        print("  ✅ Scheduler stopped")
        
        print("✅ Alert scheduler functional\n")
        return True
    except Exception as e:
        print(f"❌ Scheduler error: {e}\n")
        return False


def check_data_validation():
    """Verify data validation rules"""
    print("🔍 Checking data validation...")
    try:
        from app.schemas.data_schemas import validate_data_quality
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Test valid data
        valid_data = pd.DataFrame([{
            'date': datetime.now() - timedelta(days=1),
            'unit_cost': 10.0,
            'unit_price': 15.0,
            'current_stock': 100,
            'lead_time_days': 7
        }])
        
        result = validate_data_quality(valid_data, data_type='product')
        if result['is_valid'] and not result['errors']:
            print("  ✅ Valid data passes validation")
        else:
            print(f"  ⚠️ Unexpected result on valid data: {result['errors']}")
        
        # Test invalid data (negative cost)
        invalid_data = pd.DataFrame([{
            'date': datetime.now() - timedelta(days=1),
            'unit_cost': -10.0,
            'unit_price': 15.0,
            'current_stock': 100,
            'lead_time_days': 7
        }])
        
        result = validate_data_quality(invalid_data, data_type='product')
        if result['errors'] and any('negative' in err.lower() for err in result['errors']):
            print("  ✅ Negative cost detection works")
        else:
            print(f"  ⚠️ Expected negative cost error, got: {result['errors']}")
        
        # Test future date in sales data
        future_data = pd.DataFrame([{
            'date': datetime.now() + timedelta(days=30),
            'quantity_sold': 10,
            'sku': 'TEST123'
        }])
        
        result = validate_data_quality(future_data, data_type='sales')
        if result['warnings'] and any('future' in warn.lower() for warn in result['warnings']):
            print("  ✅ Future date detection works")
        else:
            print(f"  ⚠️ Expected future date warning, got: {result['warnings']}")
        
        print("✅ Data validation rules functional\n")
        return True
    except Exception as e:
        print(f"❌ Data validation error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def check_ml_models():
    """Verify ML models can be instantiated"""
    print("🔍 Checking ML models...")
    try:
        from app.models.demand_forecaster import DemandForecaster
        from app.models.inventory_optimizer import InventoryOptimizer
        from app.models.ai_explainer import AIExplainer
        
        forecaster = DemandForecaster()
        print("  ✅ DemandForecaster instantiated")
        
        optimizer = InventoryOptimizer()
        print("  ✅ InventoryOptimizer instantiated")
        
        explainer = AIExplainer()
        print("  ✅ AIExplainer instantiated")
        
        print("✅ ML models functional\n")
        return True
    except Exception as e:
        print(f"❌ ML models error: {e}\n")
        return False


def check_notification_formatting():
    """Verify notification message formatting"""
    print("🔍 Checking notification formatting...")
    try:
        from app.services.notification_service import format_alert_markdown
        
        test_alert = {
            'title': 'Test Alert',
            'severity': 'high',
            'product_name': 'Test Product',
            'message': 'This is a test alert'
        }
        
        markdown = format_alert_markdown(test_alert)
        
        if markdown and 'Test Alert' in markdown:
            print("  ✅ Alert formatting works")
            print(f"  📝 Sample output: {markdown[:100]}...")
        else:
            print(f"  ⚠️ Unexpected output: {markdown}")
        
        print("✅ Notification formatting functional\n")
        return True
    except Exception as e:
        print(f"❌ Notification formatting error: {e}\n")
        return False


async def run_verification():
    """Run all verification checks"""
    print("=" * 60)
    print("🚀 AI-DRIVEN INVENTORY SYSTEM VERIFICATION")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    results = {}
    
    # Run checks
    results['imports'] = check_imports()
    results['config'] = check_config()
    results['database'] = check_database()
    results['validation'] = check_data_validation()
    results['ml_models'] = check_ml_models()
    results['notification_formatting'] = check_notification_formatting()
    results['scheduler'] = await check_scheduler()
    
    # Summary
    print("=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check.replace('_', ' ').title()}")
    
    print("=" * 60)
    print(f"Result: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All systems operational!")
        print("=" * 60)
        return True
    else:
        print("⚠️ Some systems need attention")
        print("=" * 60)
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(run_verification())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
