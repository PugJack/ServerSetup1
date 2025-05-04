import discord
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

async def create_role(guild: discord.Guild, role_data: Dict[str, Any]) -> Optional[discord.Role]:
    """
    Create a role in a guild based on provided data.
    
    Args:
        guild: The guild to create the role in
        role_data: Dictionary with role properties
        
    Returns:
        The created role object or None if failed
    """
    try:
        name = role_data.get('name', 'New Role')
        color_str = role_data.get('color', '0x000000')
        color = int(color_str, 16) if isinstance(color_str, str) else color_str
        
        permissions = discord.Permissions()
        for perm_name, perm_value in role_data.get('permissions', {}).items():
            if hasattr(permissions, perm_name):
                setattr(permissions, perm_name, perm_value)
        
        role = await guild.create_role(
            name=name,
            permissions=permissions,
            color=discord.Color(color),
            hoist=role_data.get('hoist', False),
            mentionable=role_data.get('mentionable', False),
            reason="ServerSetup Bot - Role Creation"
        )
        return role
    except Exception as e:
        logger.error(f"Error creating role {role_data.get('name', 'unknown')}: {e}")
        return None

async def create_category(
    guild: discord.Guild, 
    name: str, 
    position: int = 0, 
    overwrites: Dict[discord.Role, discord.PermissionOverwrite] = None
) -> Optional[discord.CategoryChannel]:
    """
    Create a category in a guild.
    
    Args:
        guild: The guild to create the category in
        name: Name of the category
        position: Position of the category
        overwrites: Permission overwrites for the category
        
    Returns:
        The created category object or None if failed
    """
    try:
        category = await guild.create_category(
            name=name,
            position=position,
            overwrites=overwrites or {},
            reason="ServerSetup Bot - Category Creation"
        )
        return category
    except Exception as e:
        logger.error(f"Error creating category {name}: {e}")
        return None

async def create_text_channel(
    guild: discord.Guild,
    name: str,
    category: discord.CategoryChannel = None,
    topic: str = None,
    slowmode_delay: int = 0,
    nsfw: bool = False,
    overwrites: Dict[discord.Role, discord.PermissionOverwrite] = None
) -> Optional[discord.TextChannel]:
    """
    Create a text channel in a guild.
    
    Args:
        guild: The guild to create the channel in
        name: Name of the channel
        category: Category to place the channel in
        topic: Channel topic
        slowmode_delay: Slowmode delay in seconds
        nsfw: Whether the channel is NSFW
        overwrites: Permission overwrites for the channel
        
    Returns:
        The created channel object or None if failed
    """
    try:
        channel = await guild.create_text_channel(
            name=name,
            category=category,
            topic=topic,
            slowmode_delay=slowmode_delay,
            nsfw=nsfw,
            overwrites=overwrites or {},
            reason="ServerSetup Bot - Text Channel Creation"
        )
        return channel
    except Exception as e:
        logger.error(f"Error creating text channel {name}: {e}")
        return None

async def create_voice_channel(
    guild: discord.Guild,
    name: str,
    category: discord.CategoryChannel = None,
    bitrate: int = 64000,
    user_limit: int = 0,
    overwrites: Dict[discord.Role, discord.PermissionOverwrite] = None
) -> Optional[discord.VoiceChannel]:
    """
    Create a voice channel in a guild.
    
    Args:
        guild: The guild to create the channel in
        name: Name of the channel
        category: Category to place the channel in
        bitrate: Channel bitrate
        user_limit: Maximum number of users
        overwrites: Permission overwrites for the channel
        
    Returns:
        The created channel object or None if failed
    """
    try:
        channel = await guild.create_voice_channel(
            name=name,
            category=category,
            bitrate=bitrate,
            user_limit=user_limit,
            overwrites=overwrites or {},
            reason="ServerSetup Bot - Voice Channel Creation"
        )
        return channel
    except Exception as e:
        logger.error(f"Error creating voice channel {name}: {e}")
        return None

def build_permission_overwrites(
    guild: discord.Guild,
    overwrite_data: Dict[str, Dict[str, bool]]
) -> Dict[discord.Role, discord.PermissionOverwrite]:
    """
    Build permission overwrites from data.
    
    Args:
        guild: The guild for role lookup
        overwrite_data: Dictionary mapping role names to permission settings
        
    Returns:
        Dictionary of permission overwrites
    """
    overwrites = {}
    
    for role_name, permissions in overwrite_data.items():
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            overwrite = discord.PermissionOverwrite(**permissions)
            overwrites[role] = overwrite
        elif role_name == "@everyone":
            overwrite = discord.PermissionOverwrite(**permissions)
            overwrites[guild.default_role] = overwrite
    
    return overwrites
