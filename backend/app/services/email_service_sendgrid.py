"""
SendGrid Email Service - Simple & Reliable Email Delivery for POC

WHY SENDGRID:
- ✅ Free tier: 100 emails/day (perfect for POC/demos)
- ✅ No SMTP configuration needed
- ✅ High delivery success rate
- ✅ Simple API integration
- ✅ Works immediately

SETUP (2 MINUTES):
1. Go to https://signup.sendgrid.com (FREE account)
2. Verify your email address
3. Create an API Key:
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Give it a name (e.g., "Inventory POC")
   - Select "Full Access" (for POC simplicity)
   - Copy the API key (save it securely!)
4. Add to .env file or update below:
   SENDGRID_API_KEY=your_api_key_here
   FROM_EMAIL=your_verified_email@example.com

5. Verify a sender email:
   - Go to Settings → Sender Authentication
   - Click "Verify a Single Sender"
   - Fill in your details and verify

That's it! Emails will work instantly.
"""

import json
from datetime import datetime
from typing import List, Optional, Sequence

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail, To
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database.models import AlertRecipient, NotificationLog


# ============================================================================
# SENDGRID CONFIGURATION
# ============================================================================
settings = get_settings()

# SendGrid + email configuration pulled from environment / secrets manager
SENDGRID_API_KEY = settings.sendgrid_api_key
FROM_EMAIL = settings.email_from
FROM_NAME = settings.email_from_name
EMAIL_ENABLED = settings.email_enabled
DEFAULT_RECIPIENTS = settings.ensure_default_recipients()


def _serialize_list(items: Sequence[str]) -> str:
    return json.dumps(list(items))


def get_active_recipients(db: Optional[Session] = None) -> List[str]:
    """Fetch active recipients from DB, fall back to environment defaults."""
    if db:
        query = db.query(AlertRecipient).filter(
            AlertRecipient.channel == 'EMAIL',
            AlertRecipient.active.is_(True)
        )
        recipients = [record.destination for record in query.all()]
        if recipients:
            return recipients
    return DEFAULT_RECIPIENTS


def log_notification(
    db: Optional[Session],
    *,
    channel: str,
    subject: str,
    recipients: Sequence[str],
    status: str,
    response_code: Optional[int] = None,
    error_message: Optional[str] = None,
    payload: Optional[dict] = None,
    alert_key: Optional[str] = None
) -> None:
    """Persist notification attempt for auditing/debugging."""
    if not db or not settings.log_notifications:
        return

    log_entry = NotificationLog(
        channel=channel,
        subject=subject[:250],
        recipients=_serialize_list(recipients),
        status=status,
        response_code=response_code,
        error_message=error_message,
        payload=json.dumps(payload or {}) if payload else None,
        alert_key=alert_key,
        created_at=datetime.utcnow()
    )
    db.add(log_entry)
    db.commit()


# ============================================================================
# SENDGRID EMAIL FUNCTIONS
# ============================================================================

def send_email(
    to_emails: List[str],
    subject: str,
    html_content: str,
    plain_content: Optional[str] = None,
    *,
    db: Optional[Session] = None,
    alert_key: Optional[str] = None
) -> dict:
    """
    Send email via SendGrid API.
    
    Args:
        to_emails: List of recipient email addresses
        subject: Email subject line
        html_content: HTML email body
        plain_content: Plain text fallback (optional)
    
    Returns:
        dict with 'success' (bool) and 'message' (str)
    """
    if not EMAIL_ENABLED:
        print(f"[EMAIL DISABLED] Would send: {subject} to {', '.join(to_emails)}")
        return {
            'success': False,
            'message': 'Email sending is disabled. Set EMAIL_ENABLED = True to enable.'
        }
    
    if not SENDGRID_API_KEY:
        print("[EMAIL NOT CONFIGURED] SendGrid API key not set")
        return {
            'success': False,
            'message': 'SendGrid API key not configured. Set SENDGRID_API_KEY in your environment.'
        }
    
    if not to_emails:
        return {'success': False, 'message': 'No recipient email addresses provided'}
    
    try:
        # Create email message
        message = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=[To(email) for email in to_emails],
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        # Add plain text version if provided
        if plain_content:
            message.add_content(Content("text/plain", plain_content))
        
        # Send via SendGrid
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        print(f"✅ Email sent successfully to {', '.join(to_emails)}")
        print(f"   Subject: {subject}")
        print(f"   SendGrid Status: {response.status_code}")
        
        result = {
            'success': True,
            'message': f'Email sent successfully to {len(to_emails)} recipient(s)',
            'status_code': response.status_code
        }
        log_notification(
            db,
            channel='EMAIL',
            subject=subject,
            recipients=to_emails,
            status='SENT',
            response_code=response.status_code,
            payload={'alert_key': alert_key}
        )
        return result
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to send email: {error_msg}")
        
        # Provide helpful error messages
        if 'Unauthorized' in error_msg or '401' in error_msg:
            error_msg = 'Invalid SendGrid API key. Please check your configuration.'
        elif 'forbidden' in error_msg.lower() or '403' in error_msg:
            error_msg = 'Sender email not verified in SendGrid. Please verify your sender email.'
        elif '400' in error_msg:
            error_msg = f'Invalid request: {error_msg}. Check email addresses and content.'
        
        result = {
            'success': False,
            'message': f'Failed to send email: {error_msg}'
        }
        log_notification(
            db,
            channel='EMAIL',
            subject=subject,
            recipients=to_emails,
            status='FAILED',
            error_message=error_msg,
            payload={'alert_key': alert_key}
        )
        return result


def send_threshold_alert(
    product_sku: str,
    product_name: str,
    current_stock: int,
    reorder_point: int,
    recommended_qty: int,
    potential_daily_loss: float,
    category: str = None,
    recipients: Optional[List[str]] = None,
    *,
    db: Optional[Session] = None
) -> dict:
    """
    Send reorder threshold alert email.
    
    Args:
        product_sku: Product SKU code
        product_name: Product name
        current_stock: Current inventory level
        reorder_point: Configured reorder point threshold
        recommended_qty: AI-recommended reorder quantity
        potential_daily_loss: Estimated daily profit loss if stockout occurs
        category: Product category (optional)
        recipients: List of email addresses (uses DEFAULT_RECIPIENTS if not provided)
    
    Returns:
        dict with 'success' and 'message'
    """
    recipients = recipients or get_active_recipients(db)
    
    subject = f"🚨 REORDER ALERT: {product_sku} - {product_name} Below Threshold"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">⚠️ Inventory Reorder Alert</h1>
        </div>
        
        <div style="padding: 30px; background: #ffffff;">
            <p style="font-size: 16px; color: #555;">The following product has reached its reorder threshold:</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0;"><strong>Product:</strong></td>
                        <td style="padding: 8px 0;">{product_sku} - {product_name}</td>
                    </tr>
                    {f'<tr><td style="padding: 8px 0;"><strong>Category:</strong></td><td style="padding: 8px 0;">{category}</td></tr>' if category else ''}
                    <tr>
                        <td style="padding: 8px 0;"><strong>Current Stock:</strong></td>
                        <td style="padding: 8px 0;"><span style="color: #dc3545; font-weight: bold; font-size: 18px;">{current_stock} units</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Reorder Point:</strong></td>
                        <td style="padding: 8px 0;">{reorder_point} units</td>
                    </tr>
                </table>
            </div>
            
            <h3 style="color: #667eea; margin-top: 30px;">🤖 AI Recommendations:</h3>
            <div style="background: #e8eaf6; padding: 20px; border-radius: 8px; margin: 15px 0;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li style="margin: 10px 0;"><strong>Recommended Reorder Quantity:</strong> <span style="color: #667eea; font-weight: bold;">{recommended_qty} units</span></li>
                    <li style="margin: 10px 0;"><strong>Estimated Daily Loss if Stockout:</strong> <span style="color: #dc3545; font-weight: bold;">${potential_daily_loss:,.2f}</span></li>
                    <li style="margin: 10px 0;"><strong>Action Required:</strong> Order immediately to avoid lost sales</li>
                </ul>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404;"><strong>⏰ Urgent:</strong> Low stock levels may lead to stockouts and lost revenue. Please review and place orders promptly.</p>
            </div>
        </div>
        
        <div style="padding: 20px; text-align: center; background: #f8f9fa; color: #6c757d; font-size: 12px;">
            <p style="margin: 5px 0;">This is an automated alert from the AI-Powered Inventory Optimization System</p>
            <p style="margin: 5px 0;">Powered by SendGrid Email API</p>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    INVENTORY REORDER ALERT
    
    Product: {product_sku} - {product_name}
    {'Category: ' + category if category else ''}
    Current Stock: {current_stock} units
    Reorder Point: {reorder_point} units
    
    AI RECOMMENDATIONS:
    - Recommended Reorder Quantity: {recommended_qty} units
    - Estimated Daily Loss if Stockout: ${potential_daily_loss:,.2f}
    - Action Required: Order immediately to avoid lost sales
    
    This is an automated alert from the AI-Powered Inventory Optimization System.
    """
    
    return send_email(
        recipients,
        subject,
        html_content,
        plain_content,
        db=db,
        alert_key=f"threshold::{product_sku}"
    )


def send_loss_alert(
    product_sku: str,
    product_name: str,
    category: str,
    daily_loss: float,
    reason: str,
    recipients: Optional[List[str]] = None,
    *,
    db: Optional[Session] = None
) -> dict:
    """
    Send email alert for products generating losses.
    
    Args:
        product_sku: Product SKU
        product_name: Product name
        category: Product category
        daily_loss: Estimated daily loss amount
        reason: Explanation of loss (e.g., "selling below cost")
        recipients: List of email addresses (uses DEFAULT_RECIPIENTS if not provided)
    
    Returns:
        dict with 'success' and 'message'
    """
    recipients = recipients or get_active_recipients(db)
    
    subject = f"💸 LOSS ALERT: {product_sku} - Losing ${daily_loss:,.0f}/day"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 30px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">💸 Product Loss Alert</h1>
        </div>
        
        <div style="padding: 30px; background: #ffffff;">
            <p style="font-size: 16px; color: #555;">AI has detected a loss-generating product that requires immediate attention:</p>
            
            <div style="background: #ffebee; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #c62828;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0;"><strong>Product:</strong></td>
                        <td style="padding: 8px 0;">{product_sku} - {product_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Category:</strong></td>
                        <td style="padding: 8px 0;">{category}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Daily Loss:</strong></td>
                        <td style="padding: 8px 0;"><span style="color: #c62828; font-weight: bold; font-size: 20px;">${daily_loss:,.2f}</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Reason:</strong></td>
                        <td style="padding: 8px 0;">{reason}</td>
                    </tr>
                </table>
            </div>
            
            <h3 style="color: #c62828; margin-top: 30px;">⚡ Recommended Actions:</h3>
            <div style="background: #fff3e0; padding: 20px; border-radius: 8px; margin: 15px 0;">
                <ol style="margin: 0; padding-left: 20px;">
                    <li style="margin: 10px 0;">Review and adjust pricing immediately</li>
                    <li style="margin: 10px 0;">Negotiate better terms with supplier</li>
                    <li style="margin: 10px 0;">Consider promotional bundling to clear inventory</li>
                    <li style="margin: 10px 0;">Evaluate product discontinuation if losses persist</li>
                </ol>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #ffe0e0; border-radius: 8px; border-left: 4px solid #d32f2f;">
                <p style="margin: 0; color: #b71c1c;"><strong>🚨 Critical:</strong> This product is actively  losing money. Immediate action required to prevent further losses.</p>
            </div>
        </div>
        
        <div style="padding: 20px; text-align: center; background: #f8f9fa; color: #6c757d; font-size: 12px;">
            <p style="margin: 5px 0;">This is an automated alert from the AI-Powered Inventory Optimization System</p>
            <p style="margin: 5px 0;">Powered by SendGrid Email API</p>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    PRODUCT LOSS ALERT
    
    Product: {product_sku} - {product_name}
    Category: {category}
    Estimated Daily Loss: ${daily_loss:,.2f}
    Reason: {reason}
    
    RECOMMENDED ACTIONS:
    1. Review and adjust pricing immediately
    2. Negotiate better terms with supplier
    3. Consider promotional bundling to clear inventory
    4. Evaluate product discontinuation if losses persist
    
    This product is actively losing money. Immediate action required.
    """
    
    return send_email(
        recipients,
        subject,
        html_content,
        plain_content,
        db=db,
        alert_key=f"loss::{product_sku}"
    )


def send_custom_alert(
    to_emails: Optional[List[str]],
    subject: str,
    body: str,
    *,
    db: Optional[Session] = None,
    alert_key: Optional[str] = None
) -> dict:
    """
    Send custom email alert with user-provided content.
    
    Args:
        to_emails: List of recipient email addresses
        subject: Email subject
        body: Email body (can be plain text or HTML)
    
    Returns:
        dict with 'success' and 'message'
    """
    # Wrap plain text in basic HTML if not already HTML
    if not body.strip().startswith('<'):
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <pre style="white-space: pre-wrap; font-family: monospace; background: #f8f9fa; padding: 20px; border-radius: 8px;">{body}</pre>
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #6c757d; font-size: 12px;">
                <p>Sent from AI-Powered Inventory Optimization System</p>
            </div>
        </body>
        </html>
        """
    else:
        html_content = body
    
    recipients = to_emails or get_active_recipients(db)
    return send_email(
        recipients,
        subject,
        html_content,
        body,
        db=db,
        alert_key=alert_key
    )


# ============================================================================
# CONFIGURATION HELPERS
# ============================================================================

def update_api_key(api_key: str):
    """Update SendGrid API key at runtime"""
    global SENDGRID_API_KEY
    SENDGRID_API_KEY = api_key
    settings.sendgrid_api_key = api_key
    return {'success': True, 'message': 'API key updated'}


def update_from_email(email: str):
    """Update sender email at runtime"""
    global FROM_EMAIL
    FROM_EMAIL = email
    settings.email_from = email
    return {'success': True, 'message': 'Sender email updated'}


def update_recipients(recipients: List[str]):
    """Update default recipients at runtime"""
    global DEFAULT_RECIPIENTS
    DEFAULT_RECIPIENTS = recipients
    settings.default_alert_recipients = recipients
    return {'success': True, 'message': f'Recipients updated: {len(recipients)} emails'}


def toggle_email(enabled: bool):
    """Enable or disable email sending"""
    global EMAIL_ENABLED
    EMAIL_ENABLED = enabled
    settings.email_enabled = enabled
    status = 'enabled' if enabled else 'disabled'
    return {'success': True, 'message': f'Email sending {status}'}


def get_config() -> dict:
    """Get current email configuration"""
    return {
        'enabled': EMAIL_ENABLED,
        'has_api_key': bool(SENDGRID_API_KEY),
        'from_email': FROM_EMAIL,
        'from_name': FROM_NAME,
        'default_recipients': DEFAULT_RECIPIENTS,
        'provider': 'SendGrid'
    }


def test_connection() -> dict:
    """Test SendGrid configuration by sending a test email"""
    test_subject = "✅ SendGrid Test - Email Configuration Working!"
    test_body = """
    <h2>Congratulations! 🎉</h2>
    <p>Your SendGrid email integration is working correctly.</p>
    <p>You can now send stock alerts and notifications from your Inventory Optimization System.</p>
    <p><strong>SendGrid Configuration:</strong></p>
    <ul>
        <li>✅ API Key: Valid</li>
        <li>✅ Sender Email: Verified</li>
        <li>✅ Email Delivery: Working</li>
    </ul>
    """
    
    return send_email([FROM_EMAIL], test_subject, test_body)


if __name__ == "__main__":
    # Test the email service
    print("SendGrid Email Service Test")
    print("=" * 50)
    print(f"Configuration: {get_config()}")
    print("\nSending test email...")
    result = test_connection()
    print(f"Result: {result}")
