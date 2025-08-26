import discord
from discord.ui import View, Button, Select
from discord import ButtonStyle, Interaction
from database import DatabaseManager
import asyncio

# Initialize database
db = DatabaseManager()

class TicketView(View):
    def __init__(self, owner: discord.Member, category: str, slots: int, guild_id: int, channel: discord.TextChannel):
        super().__init__(timeout=None)
        self.owner = owner
        self.category = category
        self.slots = slots
        self.guild_id = guild_id
        self.channel = channel
        self.helpers = []

        self.add_item(JoinButton(self))
        self.add_item(LeaveButton(self))
        self.add_item(RemoveHelperButton(self))
        self.add_item(CloseButton(self))

    async def update_helpers_embed(self, interaction=None):
        """Update the helpers list in the embed"""
        try:
            # Get the message with the embed
            if interaction and interaction.message:
                message = interaction.message
            else:
                # Find the message with the embed in the channel
                async for msg in self.channel.history(limit=50):
                    if msg.embeds and msg.author == self.channel.guild.me:
                        message = msg
                        break
                else:
                    return  # No embed message found
            
            if not message.embeds:
                return
                
            embed = message.embeds[0]
            
            # Update helpers list
            helper_list = []
            for i in range(self.slots):
                if i < len(self.helpers):
                    helper_list.append(f"{i+1}. {self.helpers[i].mention}")
                else:
                    helper_list.append(f"{i+1}. [Empty]")
            
            # Update the helper slots field in title
            embed.set_field_at(2, name="👥 Helper Slots", value=f"{len(self.helpers)}/{self.slots} filled", inline=True)
            
            # Find and update the helpers field
            for i, field in enumerate(embed.fields):
                if field.name == "👥 Helpers":
                    embed.set_field_at(i, name="👥 Helpers", value="\n".join(helper_list), inline=False)
                    break
            
            # Update the message
            await message.edit(embed=embed, view=self)
            
        except Exception as e:
            print(f"Error updating embed: {e}")

class JoinButton(Button):
    def __init__(self, ticket_view: TicketView):
        super().__init__(label="Join as Helper", style=ButtonStyle.success, emoji="🙋")
        self.ticket_view = ticket_view

    async def callback(self, interaction: Interaction):
        try:
            # Check if user is the ticket owner (prevent them from joining as helper)
            if interaction.user == self.ticket_view.owner:
                await interaction.response.send_message("❌ You cannot join your own ticket as a helper!", ephemeral=True)
                return
                
            if interaction.user in self.ticket_view.helpers:
                await interaction.response.send_message("❌ You're already helping with this ticket!", ephemeral=True)
                return
                
            if len(self.ticket_view.helpers) >= self.ticket_view.slots:
                await interaction.response.send_message("❌ This ticket is full! All helper slots are taken.", ephemeral=True)
                return
            
            # Add helper
            self.ticket_view.helpers.append(interaction.user)
            await self.ticket_view.channel.set_permissions(interaction.user, view_channel=True, send_messages=True, read_message_history=True)
            
            # Get server config and add reward role if configured
            config = await db.get_server_config(self.ticket_view.guild_id)
            if config and config.get("reward_role_id"):
                reward_role = interaction.guild.get_role(config["reward_role_id"])
                if reward_role and reward_role not in interaction.user.roles:
                    try:
                        await interaction.user.add_roles(reward_role, reason="Joined ticket as helper")
                    except discord.Forbidden:
                        pass  # Bot doesn't have permission to add role
                    except discord.HTTPException:
                        pass  # Role hierarchy issue or other error
            
            # Update database
            await db.update_ticket_helpers(self.ticket_view.guild_id, self.ticket_view.channel.id, [h.id for h in self.ticket_view.helpers])
            
            # Update embed
            await self.ticket_view.update_helpers_embed(interaction)
            
            # Send success message
            embed = discord.Embed(
                title="✅ Successfully Joined Ticket",
                description=f"You are now helping with this **{self.ticket_view.category}** ticket!",
                color=discord.Color.green()
            )
            embed.add_field(name="🏆 Reward", value="You'll earn points when this ticket is completed", inline=True)
            embed.add_field(name="👥 Your Position", value=f"Helper #{len(self.ticket_view.helpers)}", inline=True)
            
            if config and config.get("reward_role_id"):
                reward_role = interaction.guild.get_role(config["reward_role_id"])
                if reward_role:
                    embed.add_field(name="🎭 Role Added", value=f"You now have the {reward_role.mention} role!", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Notify in channel
            await self.ticket_view.channel.send(f"🎉 {interaction.user.mention} joined as a helper! ({len(self.ticket_view.helpers)}/{self.ticket_view.slots} slots filled)")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error joining ticket: {str(e)}", ephemeral=True)

class LeaveButton(Button):
    def __init__(self, ticket_view: TicketView):
        super().__init__(label="Leave Ticket", style=ButtonStyle.secondary, emoji="👋")
        self.ticket_view = ticket_view

    async def callback(self, interaction: Interaction):
        try:
            if interaction.user not in self.ticket_view.helpers:
                await interaction.response.send_message("❌ You're not helping with this ticket!", ephemeral=True)
                return
            
            # Remove helper
            self.ticket_view.helpers.remove(interaction.user)
            await self.ticket_view.channel.set_permissions(interaction.user, overwrite=None)
            
            # Check if user has any other active tickets before removing reward role
            config = await db.get_server_config(self.ticket_view.guild_id)
            if config and config.get("reward_role_id"):
                reward_role = interaction.guild.get_role(config["reward_role_id"])
                if reward_role and reward_role in interaction.user.roles:
                    # Check if user is helping with any other tickets in this guild
                    user_helping_other_tickets = False
                    # This would require checking all active tickets, for now we keep the role
                    # In a production environment, you might want to implement this check
                    
                    # If not helping with other tickets, remove the role
                    # For now, we'll keep the role as it's safer
                    pass
            
            # Update database
            await db.update_ticket_helpers(self.ticket_view.guild_id, self.ticket_view.channel.id, [h.id for h in self.ticket_view.helpers])
            
            # Update embed
            await self.ticket_view.update_helpers_embed(interaction)
            
            # Send response
            embed = discord.Embed(
                title="👋 Left Ticket",
                description=f"You have left the **{self.ticket_view.category}** ticket.",
                color=discord.Color.orange()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Notify in channel
            await self.ticket_view.channel.send(f"👋 {interaction.user.mention} left the ticket. ({len(self.ticket_view.helpers)}/{self.ticket_view.slots} slots filled)")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error leaving ticket: {str(e)}", ephemeral=True)

class RemoveHelperButton(Button):
    def __init__(self, ticket_view: TicketView):
        super().__init__(label="Remove Helper", style=ButtonStyle.danger, emoji="🗑️")
        self.ticket_view = ticket_view

    async def callback(self, interaction: Interaction):
        try:
            # Check permissions
            config = await db.get_server_config(interaction.guild.id)
            is_admin = interaction.user.guild_permissions.administrator
            is_staff = False
            is_owner = interaction.user == self.ticket_view.owner
            
            if config:
                admin_role_id = config.get("admin_role_id")
                staff_role_id = config.get("staff_role_id")
                user_role_ids = [role.id for role in interaction.user.roles]
                
                if admin_role_id and admin_role_id in user_role_ids:
                    is_admin = True
                if staff_role_id and staff_role_id in user_role_ids:
                    is_staff = True
            
            if not (is_admin or is_staff or is_owner):
                await interaction.response.send_message("❌ Only staff, admins, or the ticket owner can remove helpers!", ephemeral=True)
                return
            
            if not self.ticket_view.helpers:
                await interaction.response.send_message("❌ No helpers to remove!", ephemeral=True)
                return

            # Create selection dropdown
            options = [
                discord.SelectOption(
                    label=h.display_name, 
                    value=str(i),
                    description=f"Remove {h.display_name} from this ticket"
                ) 
                for i, h in enumerate(self.ticket_view.helpers)
            ]
            
            select = HelperSelect(self.ticket_view, options)
            view = View(timeout=60)
            view.add_item(select)
            
            embed = discord.Embed(
                title="🗑️ Remove Helper",
                description="Select a helper to remove from this ticket:",
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error accessing remove helper: {str(e)}", ephemeral=True)

class HelperSelect(Select):
    def __init__(self, ticket_view, options):
        super().__init__(
            placeholder="Choose a helper to remove...", 
            min_values=1, 
            max_values=1, 
            options=options
        )
        self.ticket_view = ticket_view

    async def callback(self, interaction: Interaction):
        try:
            index = int(self.values[0])
            removed_helper = self.ticket_view.helpers.pop(index)
            
            # Remove permissions
            await self.ticket_view.channel.set_permissions(removed_helper, overwrite=None)
            
            # Update database
            await db.update_ticket_helpers(self.ticket_view.guild_id, self.ticket_view.channel.id, [h.id for h in self.ticket_view.helpers])
            
            # Update embed
            await self.ticket_view.update_helpers_embed()
            
            # Send response
            embed = discord.Embed(
                title="✅ Helper Removed",
                description=f"Successfully removed {removed_helper.mention} from the ticket.",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Notify in channel
            await self.ticket_view.channel.send(f"🗑️ {removed_helper.mention} was removed from the ticket by {interaction.user.mention}.")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing helper: {str(e)}", ephemeral=True)

class CloseButton(Button):
    def __init__(self, ticket_view: TicketView):
        super().__init__(label="Close Ticket", style=ButtonStyle.danger, emoji="🔒")
        self.ticket_view = ticket_view

    async def callback(self, interaction: Interaction):
        try:
            # Check permissions - only ticket owner or staff/admin can close
            config = await db.get_server_config(interaction.guild.id)
            is_owner = interaction.user == self.ticket_view.owner
            is_admin = interaction.user.guild_permissions.administrator
            is_staff = False
            
            if config:
                admin_role_id = config.get("admin_role_id") 
                staff_role_id = config.get("staff_role_id")
                user_role_ids = [role.id for role in interaction.user.roles]
                
                if admin_role_id and admin_role_id in user_role_ids:
                    is_admin = True
                if staff_role_id and staff_role_id in user_role_ids:
                    is_staff = True
            
            if not (is_owner or is_admin or is_staff):
                await interaction.response.send_message("❌ Only the ticket owner, staff, or admins can close this ticket!", ephemeral=True)
                return

            # Get point values for this category
            ticket_cog = interaction.client.get_cog("TicketCommandsCog")
            points = ticket_cog.CATEGORY_POINTS.get(self.ticket_view.category, 0) if ticket_cog else 0
            
            # Award points to helpers
            for helper in self.ticket_view.helpers:
                await db.add_user_points(self.ticket_view.guild_id, helper.id, points)

            # Mark ticket as rewarded
            await db.set_ticket_rewarded(self.ticket_view.guild_id, self.ticket_view.channel.id, True)

            # Save transcript
            await self.save_transcript(interaction.channel, interaction.user)

            # Remove from active tickets
            await db.remove_active_ticket(self.ticket_view.guild_id, self.ticket_view.channel.id)

            # Create closing embed
            embed = discord.Embed(
                title="🔒 Ticket Closed",
                description=f"This **{self.ticket_view.category}** ticket has been completed!",
                color=discord.Color.red()
            )
            embed.add_field(name="👤 Closed By", value=interaction.user.mention, inline=True)
            embed.add_field(name="🏆 Points Awarded", value=f"{points} points per helper", inline=True)
            embed.add_field(name="👥 Helpers Rewarded", value=f"{len(self.ticket_view.helpers)} helpers", inline=True)
            
            if self.ticket_view.helpers:
                helper_mentions = [h.mention for h in self.ticket_view.helpers]
                embed.add_field(name="🎉 Thank You!", value=f"Thanks to: {', '.join(helper_mentions)}", inline=False)
            
            embed.add_field(name="📄 Transcript", value="A transcript has been saved and sent to the designated channel.", inline=False)
            embed.set_footer(text="This channel will be deleted in 10 seconds...")
            
            await interaction.response.send_message(embed=embed)
            
            # Wait then delete channel
            await asyncio.sleep(10)
            await self.ticket_view.channel.delete(reason=f"Ticket closed by {interaction.user.display_name}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error closing ticket: {str(e)}", ephemeral=True)

    async def save_transcript(self, channel, closed_by):
        """Save transcript to the configured transcript channel"""
        try:
            config = await db.get_server_config(channel.guild.id)
            transcript_channel_id = config.get("transcript_channel_id")
            
            if not transcript_channel_id:
                return  # No transcript channel configured
                
            transcript_channel = channel.guild.get_channel(transcript_channel_id)
            if not transcript_channel:
                return  # Transcript channel not found
            
            # Get ticket info
            ticket_info = await db.get_active_ticket(channel.guild.id, channel.id)
            was_rewarded = ticket_info.get("rewarded", 0) == 1
            
            # Create transcript embed
            embed = discord.Embed(
                title="📄 Ticket Transcript",
                description=f"Transcript for ticket: **{channel.name}**",
                color=discord.Color.blue()
            )
            
            # Add ticket information
            embed.add_field(name="🎫 Channel", value=channel.mention, inline=True)
            embed.add_field(name="🏷️ Category", value=self.ticket_view.category, inline=True)
            embed.add_field(name="👤 Owner", value=self.ticket_view.owner.mention, inline=True)
            embed.add_field(name="🔒 Closed By", value=closed_by.mention, inline=True)
            embed.add_field(name="👥 Helpers", value=f"{len(self.ticket_view.helpers)} helpers", inline=True)
            embed.add_field(name="🏆 Rewarded", value="✅ Yes" if was_rewarded else "❌ No", inline=True)
            
            if self.ticket_view.helpers:
                helper_list = [h.mention for h in self.ticket_view.helpers]
                embed.add_field(name="🙋 Helper List", value="\n".join(helper_list), inline=False)
            
            embed.set_footer(text=f"Ticket closed on")
            embed.timestamp = discord.utils.utcnow()
            
            # Get recent messages for transcript
            messages = []
            async for message in channel.history(limit=100, oldest_first=True):
                if not message.author.bot or message.embeds:
                    timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    content = message.content if message.content else "[Embed/Attachment]"
                    messages.append(f"[{timestamp}] {message.author.display_name}: {content}")
            
            # Create transcript text file
            transcript_text = f"Ticket Transcript: {channel.name}\n"
            transcript_text += f"Category: {self.ticket_view.category}\n"
            transcript_text += f"Owner: {self.ticket_view.owner.display_name}\n"
            transcript_text += f"Closed by: {closed_by.display_name}\n"
            transcript_text += f"Helpers: {len(self.ticket_view.helpers)}\n"
            transcript_text += f"Rewarded: {'Yes' if was_rewarded else 'No'}\n"
            transcript_text += f"Closed on: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            transcript_text += "\n" + "="*50 + "\n\n"
            transcript_text += "\n".join(messages)
            
            # Create file and send
            file = discord.File(
                fp=discord.utils.io.StringIO(transcript_text),
                filename=f"transcript-{channel.name}.txt"
            )
            
            await transcript_channel.send(embed=embed, file=file)
            
        except Exception as e:
            print(f"Error saving transcript: {e}")
