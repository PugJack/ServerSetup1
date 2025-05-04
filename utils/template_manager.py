import json
import os
import time
import logging
import discord
from typing import Dict, List, Any
from utils.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class TemplateManager:
    """Manager for Discord server templates."""

    def __init__(self):
        """Initialize the template manager and load templates."""
        self.templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.templates_file = os.path.join(self.templates_path, 'server_templates.json')
        self.user_templates_file = os.path.join(self.templates_path, 'user_submitted_templates.json')
        self.backup_path = os.path.join(self.templates_path, 'backups')

        # Create directories if they don't exist
        os.makedirs(self.templates_path, exist_ok=True)
        os.makedirs(self.backup_path, exist_ok=True)

        self.templates = self._load_templates()
        self.user_templates = self._load_user_templates()

    def _load_templates(self) -> Dict[str, Any]:
        """Load server templates from JSON file."""
        try:
            with open(self.templates_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            return {}

    def _load_user_templates(self) -> Dict[str, Any]:
        """Load user-submitted templates from JSON file."""
        try:
            if os.path.exists(self.user_templates_file):
                with open(self.user_templates_file, 'r') as f:
                    return json.load(f)
            else:
                # Create empty template file if it doesn't exist
                with open(self.user_templates_file, 'w') as f:
                    json.dump({}, f)
                return {}
        except Exception as e:
            logger.error(f"Failed to load user templates: {e}")
            return {}

    def _save_user_templates(self) -> bool:
        """Save user-submitted templates to JSON file.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.user_templates_file, 'w') as f:
                json.dump(self.user_templates, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving user templates: {e}")
            return False

    def get_template_names(self) -> List[str]:
        """Get the list of template names."""
        return list(self.templates.keys())

    def get_template_list(self) -> Dict[str, str]:
        """Get a dictionary of template names and descriptions."""
        return {name: template.get('description', 'No description') for name, template in self.templates.items()}

    def get_templates_by_category(self) -> Dict[str, Dict[str, str]]:
        """Get templates organized by categories.

        Returns:
            A dictionary with categories as keys and dictionary of templates (name -> description) as values
        """
        categorized = {}

        for name, template in self.templates.items():
            # Get category or use 'Other' as default
            category = template.get('category', 'Other')

            if category not in categorized:
                categorized[category] = {}

            categorized[category][name] = template.get('description', 'No description')

        return categorized

    def get_template(self, name: str) -> Dict[str, Any]:
        """Get a specific template by name."""
        return self.templates.get(name, {})

    def generate_preview(self, template_name: str, user_id=None, guild_id=None) -> Dict[str, Any]:
        """Generate a preview of a template with categorized information.

        Args:
            template_name: The name of the template to preview
            user_id: Optional Discord user ID who is viewing the template
            guild_id: Optional Discord guild ID where template is being previewed

        Returns:
            A dictionary with preview information categorized by roles, categories, channels, etc.
        """
        template = self.get_template(template_name)
        if not template:
            return {"error": f"Template '{template_name}' not found"}

        # Track template view if user_id is provided
        if user_id:
            analytics_service.track_template_view(template_name, user_id, guild_id)

        # Extract basic information
        preview = {
            "name": template_name,
            "description": template.get("description", "No description available"),
            "category": template.get("category", "Other"),
            "image_url": template.get("image_url", None),
            "role_count": len(template.get("roles", [])),
            "category_count": len(template.get("categories", [])),
            "channel_count": sum(len(category.get("channels", [])) for category in template.get("categories", [])),
            "roles": [],
            "categories": []
        }

        # Extract role information
        for role in template.get("roles", []):
            role_info = {
                "name": role.get("name", "Unnamed Role"),
                "color": role.get("color", "0x000000"),
                "key_permissions": []
            }

            # Add notable permissions
            permissions = role.get("permissions", {})
            if permissions.get("administrator", False):
                role_info["key_permissions"].append("Administrator")
            else:
                if permissions.get("manage_guild", False):
                    role_info["key_permissions"].append("Manage Server")
                if permissions.get("manage_roles", False):
                    role_info["key_permissions"].append("Manage Roles")
                if permissions.get("manage_channels", False):
                    role_info["key_permissions"].append("Manage Channels")
                if permissions.get("kick_members", False):
                    role_info["key_permissions"].append("Kick Members")
                if permissions.get("ban_members", False):
                    role_info["key_permissions"].append("Ban Members")
                if permissions.get("manage_messages", False):
                    role_info["key_permissions"].append("Manage Messages")
                if permissions.get("priority_speaker", False):
                    role_info["key_permissions"].append("Priority Speaker")

            preview["roles"].append(role_info)

        # Extract category and channel information
        for category in template.get("categories", []):
            category_info = {
                "name": category.get("name", "Unnamed Category"),
                "channels": []
            }

            # Add channel information
            for channel in category.get("channels", []):
                channel_info = {
                    "name": channel.get("name", "Unnamed Channel"),
                    "type": channel.get("type", "text"),
                    "topic": channel.get("topic", "")
                }
                category_info["channels"].append(channel_info)

            preview["categories"].append(category_info)

        return preview

    async def apply_template(self, guild: discord.Guild, template_name: str, options: dict = None, user_id: int = None) -> None:
        """Apply a server template to a guild with optional customization.

        Args:
            guild: The Discord guild to apply the template to
            template_name: The name of the template to apply
            options: Optional dict with customization options
                include_roles: Whether to include roles
                include_categories: Whether to include categories
                include_text_channels: Whether to include text channels
                include_voice_channels: Whether to include voice channels
            user_id: The Discord user ID of who is applying the template
        """
        success = False

        try:
            # Get template data
            template = self.get_template(template_name)
            if not template:
                raise ValueError(f"Template '{template_name}' not found")

            # Default options if none provided
            if options is None:
                options = {}

            # Set default values for missing options
            include_roles = options.get('include_roles', True)
            include_categories = options.get('include_categories', True)
            include_text_channels = options.get('include_text_channels', True)
            include_voice_channels = options.get('include_voice_channels', True)

            # Setup roles and channels
            role_objects = {}

            # Create roles
            if include_roles:
                for role in template.get('roles', []):
                    try:
                        existing_role = discord.utils.get(guild.roles, name=role['name'])
                        if existing_role:
                            role_objects[role['name']] = existing_role
                            continue

                        color = int(role.get('color', '0x000000'), 16)
                        permissions = discord.Permissions()

                        # Set permissions based on template
                        for perm_name, perm_value in role.get('permissions', {}).items():
                            if hasattr(permissions, perm_name):
                                setattr(permissions, perm_name, perm_value)

                        new_role = await guild.create_role(
                            name=role['name'],
                            color=discord.Color(color),
                            permissions=permissions,
                            hoist=role.get('hoist', False),
                            mentionable=role.get('mentionable', False),
                            reason=f"ServerSetup Bot - Applying {template_name} template"
                        )
                        role_objects[role['name']] = new_role
                        logger.debug(f"Created role: {role['name']}")
                    except Exception as e:
                        logger.error(f"Error creating role {role['name']}: {e}")

            # Create categories and channels
            if include_categories:
                for category_data in template.get('categories', []):
                    try:
                        # Create category overwrites
                        overwrites = {}
                        for role_name, perms in category_data.get('permissions', {}).items():
                            role = role_objects.get(role_name) or discord.utils.get(guild.roles, name=role_name)
                            if role:
                                overwrite = discord.PermissionOverwrite(**perms)
                                overwrites[role] = overwrite

                        # Check if category exists
                        category_name = category_data['name']
                        existing_category = discord.utils.get(guild.categories, name=category_name)

                        if existing_category:
                            category = existing_category
                            # Update permissions
                            for role, overwrite in overwrites.items():
                                await category.set_permissions(role, overwrite=overwrite)
                        else:
                            # Create new category
                            category = await guild.create_category(
                                name=category_name,
                                overwrites=overwrites,
                                reason=f"ServerSetup Bot - Applying {template_name} template"
                            )
                            logger.debug(f"Created category: {category_name}")

                        # Create channels in the category
                        for channel_data in category_data.get('channels', []):
                            channel_name = channel_data['name']
                            channel_type = channel_data.get('type', 'text')

                            # Skip if channel already exists in this category
                            existing_channel = discord.utils.get(category.channels, name=channel_name)
                            if existing_channel:
                                continue

                            # Skip based on channel type and options
                            if (channel_type == 'text' and not include_text_channels) or \
                              (channel_type == 'voice' and not include_voice_channels):
                                continue

                            # Create channel overwrites
                            channel_overwrites = overwrites.copy()  # Start with category overwrites
                            for role_name, perms in channel_data.get('permissions', {}).items():
                                role = role_objects.get(role_name) or discord.utils.get(guild.roles, name=role_name)
                                if role:
                                    # Start with category overwrite if exists
                                    base_overwrite = channel_overwrites.get(role, discord.PermissionOverwrite())
                                    # Update with channel-specific permissions
                                    for perm_name, perm_value in perms.items():
                                        setattr(base_overwrite, perm_name, perm_value)
                                    channel_overwrites[role] = base_overwrite

                            if channel_type == 'text':
                                await guild.create_text_channel(
                                    name=channel_name,
                                    category=category,
                                    overwrites=channel_overwrites,
                                    topic=channel_data.get('topic', ''),
                                    slowmode_delay=channel_data.get('slowmode', 0),
                                    nsfw=channel_data.get('nsfw', False),
                                    reason=f"ServerSetup Bot - Applying {template_name} template"
                                )
                            elif channel_type == 'voice':
                                await guild.create_voice_channel(
                                    name=channel_name,
                                    category=category,
                                    overwrites=channel_overwrites,
                                    bitrate=channel_data.get('bitrate', 64000),
                                    user_limit=channel_data.get('user_limit', 0),
                                    reason=f"ServerSetup Bot - Applying {template_name} template"
                                )
                            elif channel_type == 'forum':
                                await guild.create_forum_channel(
                                    name=channel_name,
                                    category=category,
                                    overwrites=channel_overwrites,
                                    topic=channel_data.get('topic', ''),
                                    reason=f"ServerSetup Bot - Applying {template_name} template"
                                )
                            logger.debug(f"Created channel: {channel_name}")

                    except Exception as e:
                        logger.error(f"Error creating category {category_data['name']}: {e}")

            # Log completion
            logger.info(f"Successfully applied {template_name} template to guild {guild.name} ({guild.id})")
            success = True

        except Exception as e:
            logger.error(f"Error applying template {template_name} to guild {guild.name} ({guild.id}): {e}")
            success = False
            raise

        finally:
            # Track template usage if user_id is provided
            if user_id:
                # Get template data
                template_data = self.get_template(template_name)
                is_ai_generated = template_data.get('is_ai_generated', False) if template_data else False

                # Track template usage
                analytics_service.track_template_usage(
                    template_name=template_name,
                    guild_id=guild.id,
                    guild_name=guild.name,
                    user_id=user_id,
                    is_ai_generated=is_ai_generated,
                    customization_options=options,
                    success=success
                )

    async def backup_server(self, guild: discord.Guild) -> Dict[str, Any]:
        """Create a backup of the server's current structure.

        Args:
            guild: The Discord guild to backup

        Returns:
            A dictionary containing the server template data
        """
        backup = {
            "name": f"{guild.name} Backup",
            "description": f"Backup of {guild.name} created on {discord.utils.utcnow().strftime('%Y-%m-%d')}",
            "category": "Backup",
            "roles": [],
            "categories": []
        }

        # Backup roles (exclude default roles and managed roles like bot roles)
        for role in reversed(guild.roles):
            # Skip default role (@everyone) and managed roles (bot roles, etc)
            if role.is_default() or role.managed:
                continue

            role_data = {
                "name": role.name,
                "color": f"0x{role.color.value:06x}",
                "hoist": role.hoist,
                "mentionable": role.mentionable,
                "permissions": {}
            }

            # Add permissions
            for perm, value in role.permissions:
                role_data["permissions"][perm] = value

            backup["roles"].append(role_data)

        # Backup categories and channels
        for category in guild.categories:
            category_data = {
                "name": category.name,
                "permissions": {},
                "channels": []
            }

            # Add category permissions
            for target, overwrite in category.overwrites.items():
                # Only handle role overwrites for simplicity
                if isinstance(target, discord.Role) and not target.is_default() and not target.managed:
                    allow, deny = overwrite.pair()
                    perms = {}

                    # Convert permission pair to dictionary of explicit values
                    for perm, value in allow:
                        if value:
                            perms[perm] = True
                    for perm, value in deny:
                        if value:
                            perms[perm] = False

                    if perms:  # Only add if there are explicit permissions
                        category_data["permissions"][target.name] = perms

            # Backup text channels in this category
            for channel in category.text_channels:
                channel_data = {
                    "name": channel.name,
                    "type": "text",
                    "topic": channel.topic or "",
                    "slowmode": channel.slowmode_delay,
                    "nsfw": channel.is_nsfw(),
                    "permissions": {}
                }

                # Add channel-specific overwrites that differ from category
                for target, overwrite in channel.overwrites.items():
                    if isinstance(target, discord.Role) and not target.is_default() and not target.managed:
                        # Only add differences from category overwrites
                        category_overwrite = category.overwrites.get(target)
                        if category_overwrite != overwrite:  # If different from category
                            allow, deny = overwrite.pair()
                            perms = {}

                            for perm, value in allow:
                                if value:
                                    perms[perm] = True
                            for perm, value in deny:
                                if value:
                                    perms[perm] = False

                            if perms:  # Only add if there are explicit permissions
                                channel_data["permissions"][target.name] = perms

                category_data["channels"].append(channel_data)

            # Backup voice channels
            for channel in category.voice_channels:
                channel_data = {
                    "name": channel.name,
                    "type": "voice",
                    "bitrate": channel.bitrate,
                    "user_limit": channel.user_limit,
                    "permissions": {}
                }

                # Add channel-specific overwrites that differ from category
                for target, overwrite in channel.overwrites.items():
                    if isinstance(target, discord.Role) and not target.is_default() and not target.managed:
                        # Only add differences from category overwrites
                        category_overwrite = category.overwrites.get(target)
                        if category_overwrite != overwrite:  # If different from category
                            allow, deny = overwrite.pair()
                            perms = {}

                            for perm, value in allow:
                                if value:
                                    perms[perm] = True
                            for perm, value in deny:
                                if value:
                                    perms[perm] = False

                            if perms:  # Only add if there are explicit permissions
                                channel_data["permissions"][target.name] = perms

                category_data["channels"].append(channel_data)

            backup["categories"].append(category_data)

        # Save the backup to a file
        backup_filename = f"{guild.id}_{discord.utils.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        backup_file_path = os.path.join(self.backup_path, backup_filename)

        try:
            with open(backup_file_path, 'w') as f:
                json.dump(backup, f, indent=4)
            logger.info(f"Successfully created backup for guild {guild.name} ({guild.id}) at {backup_file_path}")
        except Exception as e:
            logger.error(f"Error saving backup for guild {guild.name} ({guild.id}): {e}")

        return backup

    def submit_template(self, user_id: int, template_data: Dict[str, Any]) -> bool:
        """Submit a user-created template for review.

        Args:
            user_id: Discord user ID of the submitter
            template_data: The template data to submit

        Returns:
            bool: True if submission was successful, False otherwise
        """
        try:
            # Validate template data
            required_fields = ['name', 'description', 'category', 'roles', 'categories']
            for field in required_fields:
                if field not in template_data:
                    logger.error(f"Missing required field '{field}' in template submission")
                    return False

            # Add submission metadata
            template_name = template_data['name']
            submission_time = discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')

            # Store with metadata
            if 'submissions' not in self.user_templates:
                self.user_templates['submissions'] = {}

            self.user_templates['submissions'][template_name] = {
                'data': template_data,
                'metadata': {
                    'submitted_by': user_id,
                    'submitted_at': submission_time,
                    'status': 'pending'  # pending, approved, rejected
                }
            }

            # Save to file
            success = self._save_user_templates()
            if success:
                logger.info(f"Template '{template_name}' submitted by user {user_id}")
                return True
            else:
                logger.error(f"Failed to save template submission '{template_name}' by user {user_id}")
                return False

        except Exception as e:
            logger.error(f"Error processing template submission: {e}")
            return False

    async def create_ai_template(self, guild: discord.Guild, template_name: str, description: str) -> Dict[str, Any]:
        """Placeholder for future AI template generation."""
        return {"error": "AI template generation is not currently available"}