import os
import discord
import threading
import logging
from discord.ext import commands
from discord import app_commands
from utils.template_manager import TemplateManager
from utils.analytics_service import analytics_service

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get Discord token from environment variables
TOKEN = os.getenv("DISCORD_TOKEN")

# Define intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)
template_manager = TemplateManager()

# Track bot status and rate limits
bot_status = {
    "connected": False,
    "last_connection": None,
    "reconnect_attempts": 0,
    "command_usages": {},
    "rate_limited_commands": set(),
    "active_operations": 0
}

@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""
    logger.info(f"{bot.user.name} is connected to Discord!")

    # Update bot status
    import time
    bot_status["connected"] = True
    bot_status["last_connection"] = time.time()
    bot_status["reconnect_attempts"] = 0

    # Set a status message to indicate the bot is online
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="/help | Creating servers"
        ),
        status=discord.Status.online
    )

    # Store bot client ID in an environment variable for the web interface
    client_id = str(bot.user.id) if bot.user else ""
    os.environ['DISCORD_CLIENT_ID'] = client_id
    logger.info(f"Bot client ID: {client_id}")

    # Get replit info for website URL
    # Get website URL but don't rely on its availability for core functionality
    repl_slug = os.environ.get('REPL_SLUG', 'serversetupbot')
    repl_owner = os.environ.get('REPL_OWNER', 'repl')
    website_url = f"https://{repl_slug}.{repl_owner}.repl.co"
    logger.info(f"Bot website URL set but may not be publicly accessible: {website_url}")

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

# Add Discord connection events for better error handling
@bot.event
async def on_disconnect():
    """Called when the bot disconnects from Discord."""
    import time
    bot_status["connected"] = False
    logger.warning("Bot disconnected from Discord!")

    # Update presence to show we're trying to reconnect
    try:
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Reconnecting..."
            ),
            status=discord.Status.idle
        )
    except:
        pass

@bot.event
async def on_resumed():
    """Called when the bot resumes its session after a disconnect."""
    import time
    bot_status["connected"] = True
    bot_status["last_connection"] = time.time()
    logger.info("Bot connection resumed with Discord!")

    # Update presence to show we're back online
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="/help | Creating servers"
        ),
        status=discord.Status.online
    )

@bot.event
async def on_error(event, *args, **kwargs):
    """Called when an unhandled exception occurs."""
    import traceback
    error_traceback = traceback.format_exc()
    logger.error(f"Unhandled error in {event}: {error_traceback}")

    # Set status to indicate there might be issues
    try:
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Experiencing issues..."
            ),
            status=discord.Status.dnd
        )
    except:
        pass

# Rate limiting helper function
def check_rate_limit(command_name, user_id):
    """Check if a command is rate limited for a user."""
    import time
    current_time = time.time()

    # Define cooldowns for different command types
    cooldowns = {
        "default": 3,    # 3 seconds for most commands
        "template": 30,  # 30 seconds for applying templates
        "backup": 60,    # 60 seconds for backup operations
        "ai": 120       # 120 seconds for AI operations
    }

    # Determine command type
    command_type = "default"
    if command_name in ["customize", "gaming", "community", "content", "serverhub", "promohub"]:
        command_type = "template"
    elif command_name == "backup":
        command_type = "backup"
    elif command_name == "ai-template":
        command_type = "ai"

    # Get cooldown for this command type
    cooldown = cooldowns[command_type]

    # Check if command is already in the rate limit dictionary
    command_key = f"{user_id}:{command_name}"
    if command_key in bot_status["command_usages"]:
        last_use = bot_status["command_usages"][command_key]
        if current_time - last_use < cooldown:
            # Command is rate limited
            return False, cooldown - int(current_time - last_use)

    # Update command usage time
    bot_status["command_usages"][command_key] = current_time
    return True, 0

@bot.tree.command(name="help", description="View available server templates and commands")
async def help_command(interaction: discord.Interaction):
    """Display help information and available server templates."""

    # Create page 1 - Main Commands
    page1 = discord.Embed(
        title="ServerSetup Bot - Help (1/2)",
        description="Create and manage Discord servers with pre-configured templates and tools.",
        color=discord.Color.blue()
    )

    page1.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)

    page1.add_field(
        name="📌 Essential Commands",
        value=(
            "`/help` - Shows this help message\n"
            "`/info` - View bot statistics\n"
            "`/status` - Check bot status\n"
            "`/permissions` - View permissions"
        ),
        inline=False
    )

    page1.add_field(
        name="🛠️ Server Management",
        value=(
            "`/backup` - Create server backup\n"
            "`/verification` - Setup verification\n"
            "`/ticket` - Setup ticket system\n"
            "`/customize` - Custom template options"
        ),
        inline=False
    )

    page1.add_field(
        name="🎨 Template System",
        value=(
            "`/preview` - Preview any template before applying\n"
            "`/submit-template` - Share your setup\n" 
            "`/promohub` - Promotion Hub (40+ channels)\n"
            "`/serverhub` - Server Hub (50+ channels)\n"
            "`/gaming` - Gaming template (30+ channels)\n"
            "`/community` - Community template (25+ channels)\n"
            "`/chillhangout` - Chill server for vibing\n"
            "`/sneakers` - Sneaker & streetwear community\n"
            "`/cars` - Car & motorsports enthusiasts\n"
            "`/customize` - Customize any template"
        ),
        inline=False
    )

    page1.add_field(
        name="💡 Quick Tips",
        value=(
            "• Always `/backup` before changes\n"
            "• Use `/preview` before applying\n"
            "• Check `/permissions` if needed\n"
            "• Join support server for help"
        ),
        inline=False
    )

    # Create page 2 - Templates
    page2 = discord.Embed(
        title="ServerSetup Bot - Templates (2/2)", 
        description="Available server templates by category:",
        color=discord.Color.blue()
    )

    categorized_templates = template_manager.get_templates_by_category()

    for category, templates in categorized_templates.items():
        template_list = "\n".join([f"• `/{name.lower()}` - {desc[:50]}..." 
                                 for name, desc in templates.items()])
        if template_list:
            page2.add_field(
                name=f"📂 {category}",
                value=template_list,
                inline=False
            )

    page2.set_footer(text="Use the buttons below to navigate • Join our support server for help")

    # Create navigation buttons
    class NavigationView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.current_page = 1

            # Add support server button
            support_button = discord.ui.Button(
                label="Support Server",
                style=discord.ButtonStyle.link,
                url="https://discord.gg/ZSytBRcmjA",
                emoji="🛟"
            )
            self.add_item(support_button)

        @discord.ui.button(label="◀️ Main", style=discord.ButtonStyle.blurple)
        async def show_page1(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page = 1
            await button_interaction.response.edit_message(embed=page1, view=self)

        @discord.ui.button(label="Templates ▶️", style=discord.ButtonStyle.blurple)
        async def show_page2(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            self.current_page = 2
            await button_interaction.response.edit_message(embed=page2, view=self)

    # Send initial embed with navigation
    await interaction.response.send_message(embed=page1, view=NavigationView())

@bot.tree.command(name="verification", description="Set up a verification system for your server")
async def verification(interaction: discord.Interaction):
    """Creates a verification system with button for the server."""
    if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        # Create verified role if it doesn't exist
        verified_role = discord.utils.get(interaction.guild.roles, name="Verified")
        if not verified_role:
            verified_role = await interaction.guild.create_role(
                name="Verified",
                color=discord.Color.green(),
                reason="ServerSetup Bot Verification System"
            )

        # Create verification category if it doesn't exist
        verification_category = discord.utils.get(interaction.guild.categories, name="🔒 Verification")
        if not verification_category:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=True, read_messages=True),
                verified_role: discord.PermissionOverwrite(view_channel=False)
            }
            verification_category = await interaction.guild.create_category(
                name="🔒 Verification",
                overwrites=overwrites,
                reason="ServerSetup Bot Verification System"
            )

        # Create verification channel if it doesn't exist
        verification_channel = discord.utils.get(verification_category.channels, name="verify")
        if not verification_channel:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                    read_messages=True
                ),
                verified_role: discord.PermissionOverwrite(view_channel=False)
            }
            verification_channel = await interaction.guild.create_text_channel(
                name="verify",
                category=verification_category,
                overwrites=overwrites,
                reason="ServerSetup Bot Verification System"
            )

        # Create button for verification
        verify_button = discord.ui.Button(style=discord.ButtonStyle.green, label="Verify", custom_id="verify_button")
        view = discord.ui.View()
        view.add_item(verify_button)

        # Create the embed
        embed = discord.Embed(
            title="Server Verification",
            description="Click the button below to verify and gain access to the server.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{interaction.guild.name} • Verification System")

        await verification_channel.send(embed=embed, view=view)

        # Update server settings to lock main channels for unverified users
        for category in interaction.guild.categories:
            if category.id != verification_category.id:
                try:
                    await category.set_permissions(
                        verified_role,
                        view_channel=True,
                        reason="ServerSetup Bot Verification System"
                    )
                    await category.set_permissions(
                        interaction.guild.default_role,
                        view_channel=False,
                        reason="ServerSetup Bot Verification System"
                    )
                except discord.Forbidden:
                    pass

        await interaction.followup.send("Verification system has been set up successfully!", ephemeral=True)

    except Exception as e:
        logger.error(f"Error setting up verification system: {e}")
        await interaction.followup.send(f"Error setting up verification system: {str(e)}", ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle button interactions for verification."""
    if interaction.type == discord.InteractionType.component:
        if interaction.data["custom_id"] == "verify_button":
            try:
                verified_role = discord.utils.get(interaction.guild.roles, name="Verified")
                if verified_role:
                    await interaction.user.add_roles(verified_role, reason="User verified through button")
                    await interaction.response.send_message("You have been verified! You now have access to the server.", ephemeral=True)
                    try:
                        welcome_embed = discord.Embed(
                            title="Welcome to the Server!",
                            description="Thank you for verifying! Please make sure to read our rules to ensure a great experience for everyone.",
                            color=discord.Color.green()
                        )
                        await interaction.user.send(embed=welcome_embed)
                    except:
                        pass  # User might have DMs disabled
                else:
                    await interaction.response.send_message("Verification role not found. Please contact an administrator.", ephemeral=True)
            except Exception as e:
                logger.error(f"Error during verification: {e}")
                await interaction.response.send_message("An error occurred during verification. Please try again later.", ephemeral=True)

@bot.tree.command(name="status", description="Check the bot's current connection status")
async def status_command(interaction: discord.Interaction):
    """Display the bot's current connection status."""
    import time
    current_time = time.time()

    # Get status info
    connected = bot_status["connected"]
    last_conn = bot_status["last_connection"]
    uptime = current_time - last_conn if last_conn else 0
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    # Get rate limited commands
    rate_limited = list(bot_status["rate_limited_commands"])

    # Create embed
    if connected:
        embed = discord.Embed(
            title="✅ Bot Status: Online",
            description="ServerSetup Bot is currently online and responding to commands.",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="⚠️ Bot Status: Reconnecting",
            description="ServerSetup Bot is currently trying to reconnect to Discord.",
            color=discord.Color.orange()
        )

    # Add status fields
    embed.add_field(
        name="Uptime",
        value=uptime_str,
        inline=True
    )

    embed.add_field(
        name="Active Operations",
        value=str(bot_status["active_operations"]),
        inline=True
    )

    if rate_limited:
        embed.add_field(
            name="Rate Limited Commands",
            value="\n".join(rate_limited) or "None",
            inline=False
        )

    embed.set_footer(text="Bot status is updated in real-time")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="permissions", description="Get help with permissions the bot needs")
async def permissions_guide(interaction: discord.Interaction):
    """Provides a guide on what permissions the bot needs and how to fix common issues."""
    embed = discord.Embed(
        title="📝 Permissions Guide",
        description="This guide explains what permissions ServerSetup Bot needs and how to fix common permission issues.",
        color=discord.Color.blue()
    )

    # Required permissions
    embed.add_field(
        name="🔑 Required Permissions",
        value=(
            "**Administrator** - Needed to create roles, channels, and categories\n"
            "**Manage Roles** - To create and assign roles\n"
            "**Manage Channels** - To create channels and categories\n"
            "**View Channels** - To see existing channels\n"
            "**Send Messages** - To send verification and welcome messages"
        ),
        inline=False
    )

    # Common issues
    embed.add_field(
        name="⚠️ Common Permission Issues",
        value=(
            "**1. Role Hierarchy**: The bot's role must be higher than any roles it needs to manage\n"
            "**2. Two-Factor Authentication**: If your server has 2FA requirement, bot owner needs 2FA\n"
            "**3. Discord Verification Level**: Very high verification levels may block some bot actions\n"
            "**4. Missing Scopes**: Ensure bot was invited with 'bot' and 'applications.commands' scopes"
        ),
        inline=False
    )

    # How to fix
    embed.add_field(
        name="🛠️ How to Fix Permissions",
        value=(
            "**1. Move Bot Role Up**: Server Settings > Roles > Drag bot's role higher\n"
            "**2. Reinvite the Bot**: Use the link in `/info` command with correct permissions\n"
            "**3. Check Role Settings**: Ensure Administrator permission is enabled\n"
            "**4. Server Settings**: Try lowering verification level temporarily"
        ),
        inline=False
    )

    embed.set_footer(text="If you continue having issues, join our support server for help")

    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="info", description="View detailed information about ServerSetup Bot")
async def info_command(interaction: discord.Interaction):
    """Displays detailed information about the bot."""
    # Create an embed with bot information
    embed = discord.Embed(
        title="ServerSetup Bot - Information",
        description="A Discord bot to help you create fully functional Discord server templates with pre-configured categories, channels, roles, and permissions.",
        color=discord.Color.blue()
    )

    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)

    # Bot Statistics
    guild_count = len(bot.guilds)
    template_count = len(template_manager.get_template_names())

    embed.add_field(
        name="Bot Statistics",
        value=f"Servers: {guild_count}\nAvailable Templates: {template_count}\nCommands: 14",
        inline=True
    )

    # Features
    embed.add_field(
        name="Features",
        value="• 10+ themed server templates\n• Preview templates before applying\n• Pre-configured roles & permissions\n• Styled channel names with emojis\n• Verification system with button",
        inline=True
    )

    # Links - only include guaranteed accessible links
    client_id = os.environ.get('DISCORD_CLIENT_ID', bot.user.id if bot.user else '')

    embed.add_field(
        name="Links",
        value=f"[Add to Server](https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot%20applications.commands)\n[Support Server](https://discord.gg/ZSytBRcmjA)",
        inline=False
    )

    embed.set_footer(text="Type /help to see all available commands")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="customize", description="Customize and apply a server template")
@app_commands.describe(
    template_name="The name of the template to customize",
    include_roles="Whether to include roles from the template",
    include_categories="Whether to include categories from the template",
    include_text_channels="Whether to include text channels from the template",
    include_voice_channels="Whether to include voice channels from the template"
)
async def customize_template(interaction: discord.Interaction,
                        template_name: str,
                        include_roles: bool = True,
                        include_categories: bool = True,
                        include_text_channels: bool = True,
                        include_voice_channels: bool = True):
    """Customize and apply a server template with options."""
    if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        # Get template
        template = template_manager.get_template(template_name)
        if not template:
            await interaction.followup.send(f"Template '{template_name}' not found", ephemeral=True)
            return

        # Create confirmation message
        confirmation = f"**Customizing {template_name.title()} Template**\n\n"
        confirmation += "**Selected Options:**\n"
        confirmation += f"• {'✅' if include_roles else '❌'} Roles\n"
        confirmation += f"• {'✅' if include_categories else '❌'} Categories\n"
        confirmation += f"• {'✅' if include_text_channels else '❌'} Text Channels\n"
        confirmation += f"• {'✅' if include_voice_channels else '❌'} Voice Channels\n"

        # Count what will be created
        role_count = len(template.get('roles', [])) if include_roles else 0
        category_count = len(template.get('categories', [])) if include_categories else 0

        channel_count = 0
        if include_text_channels or include_voice_channels:
            for category in template.get('categories', []):
                for channel in category.get('channels', []):
                    channel_type = channel.get('type', 'text')

                    if (channel_type == 'text' and include_text_channels) or \
                       (channel_type == 'voice' and include_voice_channels):
                        channel_count += 1

        confirmation += f"\n**Will create:** {role_count} roles, {category_count} categories, and {channel_count} channels."

        # Create class to hold template options
        template_options = {
            'include_roles': include_roles,
            'include_categories': include_categories,
            'include_text_channels': include_text_channels,
            'include_voice_channels': include_voice_channels
        }

        # Apply template with options and track user for analytics
        from app import app
        with app.app_context():
            await template_manager.apply_template(interaction.guild, template_name, template_options, interaction.user.id)

        # Send confirmation
        await interaction.followup.send(
            f"{confirmation}\n\n✅ Template applied successfully with your customizations!",
            ephemeral=True
        )

    except Exception as e:
        logger.error(f"Error customizing template: {e}")
        await interaction.followup.send(f"Error customizing template: {str(e)}", ephemeral=True)

@bot.tree.command(name="ticket", description="Set up the ticket system")
async def setup_ticket(interaction: discord.Interaction):
    if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
        return
    """Creates a ticket channel with a button for users to create tickets."""
    if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        # Create ticket category if it doesn't exist
        ticket_category = discord.utils.get(interaction.guild.categories, name="🎫 Support Tickets")
        if not ticket_category:
            ticket_category = await interaction.guild.create_category(
                name="🎫 Support Tickets",
                reason="ServerSetup Bot Ticket System"
            )

        # Create ticket channel if it doesn't exist
        ticket_channel = discord.utils.get(ticket_category.channels, name="create-ticket")
        if not ticket_channel:
            ticket_channel = await interaction.guild.create_text_channel(
                name="create-ticket",
                category=ticket_category,
                topic="Create a support ticket here",
                reason="ServerSetup Bot Ticket System"
            )

        class TicketButton(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)

            @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket")
            async def create_ticket(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                class TicketModal(discord.ui.Modal, title="Create Support Ticket"):
                    reported_user = discord.ui.TextInput(
                        label="Who are you reporting?",
                        placeholder="Leave blank if not reporting anyone",
                        required=False,
                        style=discord.TextStyle.short
                    )
                    ticket_reason = discord.ui.TextInput(
                        label="What is your reason for creating this ticket?",
                        placeholder="Give detail so we can help you more efficiently",
                        required=True,
                        style=discord.TextStyle.paragraph
                    )

                    async def on_submit(self, modal_interaction: discord.Interaction):
                        if not interaction.guild:
                            return

                        # Create ticket channel name
                        channel_name = f"ticket-{interaction.user.name.lower()}"

                        # Set up permissions
                        staff_role = discord.utils.get(interaction.guild.roles, name="Staff")
                        overwrites = {
                            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        }
                        if staff_role:
                            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                        # Create the ticket channel
                        try:
                            ticket_channel = await interaction.guild.create_text_channel(
                                name=channel_name,
                                overwrites=overwrites,
                                reason=f"Ticket created by {interaction.user}"
                            )

                            # Create ticket embed
                            embed = discord.Embed(
                                title="New Support Ticket",
                                color=discord.Color.blue(),
                                timestamp=discord.utils.utcnow()
                            )
                            embed.add_field(name="Created by", value=interaction.user.mention, inline=False)
                            if self.reported_user.value:
                                embed.add_field(name="Reported User", value=self.reported_user.value, inline=False)
                            embed.add_field(name="Reason", value=self.ticket_reason.value, inline=False)

                            await ticket_channel.send(embed=embed)
                            if staff_role:
                                await ticket_channel.send(f"{staff_role.mention} A new ticket has been created.")

                            await modal_interaction.response.send_message(
                                        f"Ticket created! Please check {ticket_channel.mention}",
                                        ephemeral=True
                                    )
                        except Exception as e:
                            await modal_interaction.response.send_message(
                                "Failed to create ticket channel. Please ensure I have proper permissions.",
                                ephemeral=True
                            )

                await button_interaction.response.send_modal(TicketModal())

        # Create the embed for the ticket channel
        embed = discord.Embed(
            title="🎫 Support Ticket System",
            description="Need help? Click the button below to create a support ticket.\nA staff member will assist you as soon as possible.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"{interaction.guild.name} • Support Tickets")

        # Send the embed with the button
        await ticket_channel.send(embed=embed, view=TicketButton())
        await interaction.followup.send("Ticket system has been set up successfully!", ephemeral=True)

    except Exception as e:
        logger.error(f"Error setting up ticket system: {e}")
        await interaction.followup.send(f"Error setting up ticket system: {str(e)}", ephemeral=True)


@bot.tree.command(name="preview", description="Preview a server template before applying it")
@app_commands.describe(template_name="The name of the template to preview")
async def preview_template(interaction: discord.Interaction, template_name: str):
    """Preview a server template before applying it."""
    try:
        from app import app
        with app.app_context():
            # Get template preview information and track view analytics
            preview_data = template_manager.generate_preview(
                template_name,
                user_id=interaction.user.id,
                guild_id=interaction.guild.id if interaction.guild else None
            )

        if "error" in preview_data:
            await interaction.response.send_message(preview_data["error"], ephemeral=True)
            return

        # Create embed for template overview
        overview_embed = discord.Embed(
            title=f"📋 {preview_data['name'].title()} Template Preview",
            description=preview_data['description'],
            color=discord.Color.blue()
        )

        # Set thumbnail if available
        if preview_data.get('image_url'):
            overview_embed.set_thumbnail(url=preview_data['image_url'])

        # Add summary stats
        overview_embed.add_field(
            name="Summary",
            value=f"🧩 **{preview_data['category_count']}** Categories\n" +
                  f"📝 **{preview_data['channel_count']}** Channels\n" +
                  f"👑 **{preview_data['role_count']}** Roles",
            inline=False
        )

        # Add roles information
        roles_text = ""
        for role in preview_data['roles'][:10]:  # Limit to 10 roles to avoid oversized embeds
            color_hex = role['color']
            permissions = ", ".join(role['key_permissions']) if role['key_permissions'] else "No special permissions"
            roles_text += f"**{role['name']}** - {permissions}\n"

        if len(preview_data['roles']) > 10:
            roles_text += f"*...and {len(preview_data['roles']) - 10} more roles*\n"

        overview_embed.add_field(name="📊 Roles", value=roles_text or "No roles defined", inline=False)

        # Add first few categories and channels preview
        categories_text = ""
        for i, category in enumerate(preview_data['categories'][:5]):  # Limit to 5 categories
            categories_text += f"**{category['name']}**\n"

            # Add first few channels from this category
            channel_list = []
            for channel in category['channels'][:5]:  # Limit to 5 channels per category
                # Add an emoji based on channel type
                emoji = "🔊" if channel['type'] == "voice" else "📋" if channel['type'] == "forum" else "#️⃣"
                channel_list.append(f"{emoji} {channel['name']}")

            if channel_list:
                categories_text += "  " + "\n  ".join(channel_list) + "\n"

            # If there are more channels, add a note
            if len(category['channels']) > 5:
                categories_text += f"  *...and {len(category['channels']) - 5} more channels*\n"

        # If there are more categories, add a note
        if len(preview_data['categories']) > 5:
            categories_text += f"*...and {len(preview_data['categories']) - 5} more categories*\n"

        overview_embed.add_field(name="📂 Categories & Channels", value=categories_text or"No categories defined", inline=False)

        # Add a footer with instructions
        overview_embed.set_footer(text=f"Use the /{template_name.lower()} command to apply this template to yourserver")

        # Send the preview embed
        await interaction.response.send_message(embed=overview_embed)

    except Exception as e:
        logger.error(f"Error generating template preview: {e}")
        await interaction.response.send_message(f"Error generating preview: {str(e)}", ephemeral=True)

@bot.tree.command(name="promohub", description="Create a Server Promotion Hub with 40+ advertisement channels")
@app_commands.checks.has_permissions(administrator=True)
async def promohub(interaction: discord.Interaction):
    """Creates a Server Promotion Hub with 40+ advertisement channels."""
    if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        from app import app
        with app.app_context():
            await template_manager.apply_template(interaction.guild, "promohub", user_id=interaction.user.id)

        # Success message with preview tip
        await interaction.followup.send(
            "Server Promotion Hub template applied successfully! Your server now has 40+ promotion channels set up with appropriate roles and permissions.\n\n" +
            "💡 Tip: Next time you can use `/preview promohub` to see what's included before applying a template.",
            ephemeral=True
        )
    except Exception as e:
        logger.error(f"Error applying Promotion Hub template: {e}")
        await interaction.followup.send(f"Error applying Promotion Hub template: {str(e)}", ephemeral=True)

@bot.tree.command(name="serverhub", description="Create a Server Hub template with 50+ channels")
@app_commands.checks.has_permissions(administrator=True)
async def serverhub(interaction: discord.Interaction):
    """Creates a Server Hub template with 50+ channels."""
    if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        from app import app
        with app.app_context():
            await template_manager.apply_template(interaction.guild, "serverhub", user_id=interaction.user.id)

        # Success message with preview tip
        await interaction.followup.send(
            "Server Hub template applied successfully! Your server now has 50+ channels set up with appropriate roles and permissions.\n\n" +
            "💡 Tip: Next time you can use `/preview serverhub` to see what's included before applying a template.",
            ephemeral=True
        )
    except Exception as e:
        logger.error(f"Error applying Server Hub template: {e}")
        await interaction.followup.send(f"Error applying Server Hub template: {str(e)}", ephemeral=True)

@bot.tree.command(name="backup", description="Create a backup of your server's current structure")
async def backup_command(interaction: discord.Interaction):
    if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
        return
    """Creates a backup of the server's current structure."""
    if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        # Create the backup
        await interaction.followup.send("Creating server backup... This may take a moment.", ephemeral=True)
        backup = await template_manager.backup_server(interaction.guild)

        # Create successful backup message
        embed = discord.Embed(
            title="Server Backup Created",
            description=f"A backup of **{interaction.guild.name}** has been created successfully!",
            color=discord.Color.green()
        )

        # Add statistics
        embed.add_field(
            name="Backup Statistics",
            value=f"Roles: {len(backup['roles'])}\nCategories: {len(backup['categories'])}\nTotal Channels: {sum(len(category['channels']) for category in backup['categories'])}",
            inline=False
        )

        embed.add_field(
            name="Backup Usage",
            value="Your server backup can be used to restore your server setup or create a template for others to use. The backup has been saved to the bot's secure storage.",
            inline=False
        )

        embed.set_footer(text=f"Backup ID: {interaction.guild.id}_{discord.utils.utcnow().strftime('%Y%m%d_%H%M%S')}")

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Error creating server backup: {e}")
        await interaction.followup.send(f"Error creating server backup: {str(e)}", ephemeral=True)

@bot.tree.command(name="submit-template", description="Submit your server as a template for others to use")
@app_commands.describe(
    name="A name for your template",
    description="A description of what your template is for",
    category="The category your template belongs to"
)
async def submit_template_command(interaction: discord.Interaction,
                                 name: str,
                                 description: str,
                                 category: str):
    """Submit your server as a template for others to use."""
    if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        # Create a backup of the server to use as the template
        backup = await template_manager.backup_server(interaction.guild)

        # Modify the backup with the template metadata
        template_data = backup.copy()
        template_data["name"] = name
        template_data["description"] = description
        template_data["category"] = category

        # Submit the template
        success = template_manager.submit_template(interaction.user.id, template_data)

        if success:
            embed = discord.Embed(
                title="Template Submitted",
                description=f"Your template **{name}** has been submitted for review!",
                color=discord.Color.green()
            )

            embed.add_field(
                name="Next Steps",
                value="Your template will be reviewed by our team. If approved, it will be made available to all users of ServerSetup Bot.",
                inline=False
            )

            embed.add_field(
                name="Template Details",
                value=f"**Name:** {name}\n**Category:** {category}\n**Description:** {description}",
                inline=False
            )

            embed.set_footer(text="Thank you for contributing to the ServerSetup Bot community!")

            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("Error submitting template. Please try again later.", ephemeral=True)

    except Exception as e:
        logger.error(f"Error submitting template: {e}")
        await interaction.followup.send(f"Error submitting template: {str(e)}", ephemeral=True)



# Create commands for all server templates
for template_name in template_manager.get_template_names():
    # Skip serverhub and promohub as they're already defined explicitly above
    if template_name.lower() in ["serverhub", "promohub"]:
        continue

    @bot.tree.command(name=template_name.lower(), description=f"Create a {template_name} server template")
    @app_commands.checks.has_permissions(administrator=True)
    async def template_command(interaction: discord.Interaction, template_name: str = template_name):
        if not interaction.guild or interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("This command can only be used by the server owner!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            from app import app
            with app.app_context():
                await template_manager.apply_template(
                    interaction.guild,
                    template_name,
                    user_id=interaction.user.id
                )
                await interaction.followup.send(f"Successfully applied the {template_name} template!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error applying {template_name} template: {e}")
            await interaction.followup.send(f"Error applying {template_name} template: {str(e)}", ephemeral=True)

# Add a decorator for rate limiting and error handling
def rate_limit_and_handle_errors():
    """Decorator to handle rate limiting and errors for commands."""
    def decorator(func):
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            # Get command name from the function name
            command_name = func.__name__
            if command_name.endswith("_command"):
                command_name = command_name[:-8]  # Strip _command suffix

            # Check rate limit
            allowed, wait_time = check_rate_limit(command_name, interaction.user.id)
            if not allowed:
                await interaction.response.send_message(
                    f"⏱️ This command is on cooldown. Please wait {wait_time} more seconds before using it again.",
                    ephemeral=True
                )
                bot_status["rate_limited_commands"].add(command_name)
                return

            # Remove from rate limited set if it was there
            if command_name in bot_status["rate_limited_commands"]:
                bot_status["rate_limited_commands"].remove(command_name)

            # Track active operations
            bot_status["active_operations"] += 1

            try:
                # Run the command
                await func(interaction, *args, **kwargs)
            except discord.Forbidden as e:
                # Permission error
                logger.error(f"Permission error in {command_name}: {e}")
                embed = discord.Embed(
                    title="⚠️ Permission Error",
                    description=f"The bot doesn't have permission to perform this action.\n\nError: {str(e)}",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="How to fix this",
                    value="Use `/permissions` to see what permissions the bot needs and how to fix common permission issues.",
                    inline=False
                )

                try:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.HTTPException as e:
                # Discord API error
                logger.error(f"Discord API error in {command_name}: {e}")

                if e.status == 429:  # Rate limit error
                    bot_status["rate_limited_commands"].add(command_name)
                    embed = discord.Embed(
                        title="⏱️ Rate Limited",
                        description="Discord is rate-limiting the bot. Please try again in a few minutes.",
                        color=discord.Color.orange()
                    )
                else:
                    embed = discord.Embed(
                        title="⚠️ Discord Error",
                        description=f"An error occurred with Discord's servers.\n\nError: {e.text}",
                        color=discord.Color.red()
                    )

                try:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except:
                    await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                # General error
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Error in {command_name}: {error_traceback}")

                embed = discord.Embed(
                    title="❌ Error",
                    description=f"An unexpected error occurred.\n\nError: {str(e)}",
                    color=discord.Color.red()
                )

                # Add a button to report the error
                view = discord.ui.View()
                report_button = discord.ui.Button(
                    label="Report This Error",
                    style=discord.ButtonStyle.link,
                    url="https://discord.gg/ZSytBRcmjA"
                )
                view.add_item(report_button)

                try:
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                except:
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            finally:
                # Decrease active operations
                bot_status["active_operations"] -= 1

        return wrapper
    return decorator

def start_bot():
    """Start the Discord bot in a separate thread."""
    def run_bot():
        import time

        if TOKEN:
            # Set initial bot status values
            bot_status["last_connection"] = time.time()

            # Set up auto-reconnect
            max_retries = 5
            retry_delay = 5  # seconds
            retry_count = 0

            while retry_count < max_retries:
                try:
                    bot.run(TOKEN, reconnect=True)
                    break  # Bot exited normally
                except Exception as e:
                    logger.error(f"Bot runtime error (attempt {retry_count+1}/{max_retries}): {e}")
                    bot_status["connected"] = False
                    bot_status["reconnect_attempts"] += 1
                    retry_count += 1

                    if retry_count < max_retries:
                        logger.info(f"Reconnecting in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.critical("Maximum retry attempts reached. Bot is shutting down.")
        else:
            logger.error("No Discord token found! Bot cannot start.")

    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    return thread

@bot.tree.command(name="review-templates", description="Review pending template submissions")
@app_commands.checks.has_permissions(administrator=True)
async def review_templates(interaction: discord.Interaction):
    """Review pending template submissions."""
    # Check if the user is the bot creator (replace with your Discord user ID)
    BOT_CREATOR_ID = 737485882419839056  # Your Discord user ID

    if interaction.user.id != BOT_CREATOR_ID:
        await interaction.response.send_message("Only the bot creator can review templates.", ephemeral=True)
        return

    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server!", ephemeral=True)
        return

    await interaction.response.send_message("Template review functionality coming soon!", ephemeral=True)

# Apply the rate limiting and error handling decorator to all commands
for command in bot.tree.get_commands():
    command.callback = rate_limit_and_handle_errors()(command.callback)

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        logger.error("No Discord token found! Bot cannot start.")