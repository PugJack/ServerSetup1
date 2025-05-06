import logging
from datetime import datetime
from models import TemplateUsage, TemplateAnalytics, TemplateView
from app import db

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for tracking template usage analytics"""

    @staticmethod
    def track_template_usage(template_name, guild_id, guild_name, user_id, is_ai_generated=False, 
                             customization_options=None, success=True):
        """Track template usage

        Args:
            template_name: Name of the template used
            guild_id: Discord guild ID where template was applied
            guild_name: Name of the Discord guild
            user_id: Discord user ID who applied the template
            is_ai_generated: Whether this is an AI-generated template
            customization_options: Dict of customization options used
            success: Whether the template application was successful
        """
        try:
            # Record the usage event
            usage = TemplateUsage(
                template_name=template_name,
                guild_id=guild_id,
                guild_name=guild_name,
                user_id=user_id,
                is_ai_generated=is_ai_generated,
                customization_options=customization_options,
                success=success
            )
            db.session.add(usage)

            # Update or create template analytics
            analytics = TemplateAnalytics.query.filter_by(template_name=template_name).first()
            if not analytics:
                analytics = TemplateAnalytics(template_name=template_name)
                db.session.add(analytics)

            # Safely update statistics by treating None as 0
            analytics.total_uses = (analytics.total_uses or 0) + 1

            if success:
                analytics.successful_uses = (analytics.successful_uses or 0) + 1
            else:
                analytics.failed_uses = (analytics.failed_uses or 0) + 1

            if is_ai_generated:
                analytics.ai_generated_uses = (analytics.ai_generated_uses or 0) + 1

            analytics.last_updated = datetime.utcnow()

            # Commit the changes
            db.session.commit()
            logger.info(f"Tracked usage of template '{template_name}' by user {user_id} in guild {guild_id}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error tracking template usage: {e}")

    @staticmethod
    def track_template_view(template_name, user_id, guild_id=None):
        """Track template view/preview

        Args:
            template_name: Name of the template viewed
            user_id: Discord user ID who viewed the template
            guild_id: Discord guild ID where template was viewed (optional)
        """
        try:
            view = TemplateView(
                template_name=template_name,
                user_id=user_id,
                guild_id=guild_id
            )
            db.session.add(view)
            db.session.commit()
            logger.debug(f"Tracked view of template '{template_name}' by user {user_id}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error tracking template view: {e}")

    @staticmethod
    def get_popular_templates(limit=10, period_days=30):
        """Get most popular templates by usage count

        Args:
            limit: Maximum number of templates to return
            period_days: Period for analytics in days (0 = all time)

        Returns:
            List of template analytics ordered by popularity
        """
        try:
            query = TemplateAnalytics.query.order_by(TemplateAnalytics.total_uses.desc())
            return query.limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting popular templates: {e}")
            return []

    @staticmethod
    def get_template_stats(template_name):
        """Get analytics for a specific template

        Args:
            template_name: Name of the template to get stats for

        Returns:
            TemplateAnalytics object or None if not found
        """
        try:
            return TemplateAnalytics.query.filter_by(template_name=template_name).first()
        except Exception as e:
            logger.error(f"Error getting template stats for '{template_name}': {e}")
            return None

# Create a global instance
analytics_service = AnalyticsService()
