import os
import logging

logger = logging.getLogger(__name__)

def send_verification_email(to_email: str, display_name: str, verification_url: str) -> bool:
    """Send verification email to user. Returns True on success."""
    api_key = os.environ.get("RESEND_API_KEY")
    email_from = os.environ.get("EMAIL_FROM", "ChatControl <noreply@chatcontrol.app>")
    
    if not api_key:
        logger.warning("RESEND_API_KEY not set — email not sent to %s", to_email)
        logger.info("Verification URL for %s: %s", display_name, verification_url)
        return False
    
    try:
        import resend
        resend.api_key = api_key
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">ChatControl</h1>
            </div>
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Confirma tu email</h2>
                <p>Hola <strong>{display_name}</strong>,</p>
                <p>Para completar tu registro en ChatControl, por favor confirma tu email haciendo clic en el siguiente botón:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Confirmar Email</a>
                </div>
                <p style="color: #666; font-size: 14px;"><strong>Este enlace expira en 15 minutos.</strong></p>
                <p style="color: #666; font-size: 14px;">Si no solicitaste este registro, puedes ignorar este mensaje.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">© 2026 ChatControl. Todos los derechos reservados.</p>
            </div>
        </body>
        </html>
        """
        
        params = {
            "from": email_from,
            "to": [to_email],
            "subject": "Confirma tu email para ChatControl",
            "html": html_content,
        }
        
        result = resend.Emails.send(params)
        logger.info("Verification email sent to %s", to_email)
        return True
    except ImportError:
        logger.warning("resend package not installed — email not sent")
        return False
    except Exception as e:
        logger.error("Failed to send verification email: %s", e)
        return False
