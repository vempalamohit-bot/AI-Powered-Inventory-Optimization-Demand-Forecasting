"""Email Notification Service for Threshold Alerts

TO ENABLE EMAIL NOTIFICATIONS:
1. Configure your SMTP settings below
2. Update the recipient email list
3. Call send_threshold_alert() when a product reaches reorder threshold

Example usage:
    from app.services.email_service import send_threshold_alert
    
    send_threshold_alert(
        product_sku="ABC123",
        product_name="Widget A",
        current_stock=5,
        reorder_point=20,
        recommended_qty=100,
        potential_daily_loss=1500.0
    )
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List


# ============================================================================
# SMTP CONFIGURATION (update these with your actual email server details)
# ============================================================================
SMTP_ENABLED = False  # Set to True once you configure SMTP below
SMTP_HOST = "smtp.gmail.com"  # or your mail server
SMTP_PORT = 587
SMTP_USERNAME = "your-email@example.com"
SMTP_PASSWORD = "your-app-password"  # Use app-specific password for Gmail
FROM_EMAIL = "inventory-alerts@example.com"
ALERT_RECIPIENTS = [
    "inventory-manager@example.com",
    "purchasing@example.com",
]


def send_threshold_alert(
    product_sku: str,
    product_name: str,
    current_stock: int,
    reorder_point: int,
    recommended_qty: int,
    potential_daily_loss: float,
    category: str = None
) -> bool:
    """Send email alert when product reaches reorder threshold.
    
    Args:
        product_sku: Product SKU code
        product_name: Product name
        current_stock: Current inventory level
        reorder_point: Configured reorder point threshold
        recommended_qty: AI-recommended reorder quantity
        potential_daily_loss: Estimated daily profit loss if stockout occurs
        category: Product category (optional)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not SMTP_ENABLED:
        print(f"[EMAIL DISABLED] Would send alert for {product_sku} - {product_name}")
        return False
    
    subject = f"🚨 REORDER ALERT: {product_sku} - {product_name} Below Threshold"
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #d32f2f;">⚠️ Inventory Reorder Alert</h2>
        
        <p>The following product has reached its reorder threshold:</p>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p><strong>Product:</strong> {product_sku} - {product_name}</p>
            {f'<p><strong>Category:</strong> {category}</p>' if category else ''}
            <p><strong>Current Stock:</strong> <span style="color: #d32f2f; font-weight: bold;">{current_stock} units</span></p>
            <p><strong>Reorder Point:</strong> {reorder_point} units</p>
        </div>
        
        <h3 style="color: #1976d2;">AI Recommendations:</h3>
        <ul style="background: #e3f2fd; padding: 15px 15px 15px 35px; border-radius: 8px;">
            <li><strong>Recommended Reorder Quantity:</strong> {recommended_qty} units</li>
            <li><strong>Estimated Daily Loss if Stockout:</strong> ${potential_daily_loss:,.2f}</li>
            <li><strong>Action Required:</strong> Order immediately to avoid lost sales</li>
        </ul>
        
        <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.9em; color: #666;">
            This is an automated alert from the AI-Powered Inventory Optimization System.<br>
            To adjust alert thresholds or recipients, contact your system administrator.
        </p>
    </body>
    </html>
    """
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = ", ".join(ALERT_RECIPIENTS)
        
        msg.attach(MIMEText(body_html, 'html'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Alert email sent for {product_sku} - {product_name}")
        return True
    
    except Exception as e:
        print(f"❌ Failed to send email alert for {product_sku}: {e}")
        return False


def send_loss_alert(
    product_sku: str,
    product_name: str,
    category: str,
    daily_loss: float,
    reason: str
) -> bool:
    """Send email alert for products generating losses.
    
    Args:
        product_sku: Product SKU
        product_name: Product name
        category: Product category
        daily_loss: Estimated daily loss amount
        reason: Explanation of loss (e.g., "selling below cost")
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not SMTP_ENABLED:
        print(f"[EMAIL DISABLED] Would send loss alert for {product_sku}")
        return False
    
    subject = f"💸 LOSS ALERT: {product_sku} - Losing ${daily_loss:,.0f}/day"
    
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #c62828;">💸 Product Loss Alert</h2>
        
        <p>AI has detected a loss-generating product:</p>
        
        <div style="background: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #c62828;">
            <p><strong>Product:</strong> {product_sku} - {product_name}</p>
            <p><strong>Category:</strong> {category}</p>
            <p><strong>Estimated Daily Loss:</strong> <span style="color: #c62828; font-weight: bold; font-size: 1.2em;">${daily_loss:,.2f}</span></p>
            <p><strong>Reason:</strong> {reason}</p>
        </div>
        
        <h3 style="color: #d32f2f;">Recommended Actions:</h3>
        <ul style="background: #fff3e0; padding: 15px 15px 15px 35px; border-radius: 8px;">
            <li>Review and adjust pricing immediately</li>
            <li>Negotiate better terms with supplier</li>
            <li>Consider promotional bundling to clear inventory</li>
            <li>Evaluate product discontinuation if losses persist</li>
        </ul>
        
        <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.9em; color: #666;">
            This is an automated alert from the AI-Powered Inventory Optimization System.
        </p>
    </body>
    </html>
    """
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = ", ".join(ALERT_RECIPIENTS)
        
        msg.attach(MIMEText(body_html, 'html'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Loss alert email sent for {product_sku}")
        return True
    
    except Exception as e:
        print(f"❌ Failed to send loss alert for {product_sku}: {e}")
        return False


# ============================================================================
# INTEGRATION EXAMPLE (to be called from routes.py or scheduled jobs)
# ============================================================================
def check_and_send_alerts(db):
    """Example function to check thresholds and send alerts.
    
    This would be called:
    - From a scheduled background job (e.g., celery task every hour)
    - From the live_alerts endpoint when threshold is crossed
    - From a webhook when inventory is updated
    """
    from ..database.models import Product
    from ..models.reorder_calculator import ReorderCalculator
    
    products = db.query(Product).all()
    
    for product in products:
        try:
            reorder_info = ReorderCalculator.calculate_reorder_point(db, product.id)
            stockout_risk = ReorderCalculator.calculate_stockout_risk(db, product.id)
            
            # Check if below reorder point
            if product.current_stock <= reorder_info['reorder_point']:
                send_threshold_alert(
                    product_sku=product.sku,
                    product_name=product.name,
                    current_stock=product.current_stock,
                    reorder_point=reorder_info['reorder_point'],
                    recommended_qty=reorder_info['safety_stock'] * 2,
                    potential_daily_loss=stockout_risk.get('average_daily_demand', 0) * 
                                       (product.unit_price - product.unit_cost),
                    category=product.category
                )
            
            # Check if loss-making
            unit_margin = product.unit_price - product.unit_cost
            if unit_margin < 0:
                avg_daily = stockout_risk.get('average_daily_demand', 0)
                daily_loss = abs(unit_margin) * avg_daily
                send_loss_alert(
                    product_sku=product.sku,
                    product_name=product.name,
                    category=product.category,
                    daily_loss=daily_loss,
                    reason=f"Selling at ${product.unit_price:.2f} but cost is ${product.unit_cost:.2f}"
                )
        
        except Exception as e:
            continue
