from app import db
from datetime import datetime

class TemplateUsage(db.Model):
    """Model to track template usage statistics"""
    id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(100), nullable=False, index=True)
    guild_id = db.Column(db.BigInteger, nullable=False)
    guild_name = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.BigInteger, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_ai_generated = db.Column(db.Boolean, default=False)
    customization_options = db.Column(db.JSON, nullable=True)
    success = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f"<TemplateUsage {self.template_name} by {self.user_id} at {self.timestamp}>"

class TemplateAnalytics(db.Model):
    """Model to store aggregated template analytics"""
    id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(100), nullable=False, unique=True)
    total_uses = db.Column(db.Integer, default=0)
    successful_uses = db.Column(db.Integer, default=0)
    failed_uses = db.Column(db.Integer, default=0)
    ai_generated_uses = db.Column(db.Integer, default=0)
    unique_guilds = db.Column(db.Integer, default=0)
    unique_users = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TemplateAnalytics {self.template_name} used {self.total_uses} times>"

class TemplateView(db.Model):
    """Model to track template preview/view statistics"""
    id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.BigInteger, nullable=False)
    guild_id = db.Column(db.BigInteger, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TemplateView {self.template_name} by {self.user_id} at {self.timestamp}>"
