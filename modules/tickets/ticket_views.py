import discord
from discord.ui import View, Button, Select
from discord import ButtonStyle, Interaction
from database import DatabaseManager
import asyncio
import io

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
            # Check if user has helper role
            if not interaction.guild or not isinstance(interaction.user, discord.Member):
                await interaction.response.send_message("❌ Error: This command can only be used in servers!", ephemeral=True)
                return
                
            config = await db.get_server_config(interaction.guild.id)
            has_helper_role = False
            is_admin = interaction.user.guild_permissions.administrator
            is_staff = False
            
            if config:
                helper_role_id = config.get("helper_role_id")
                admin_role_id = config.get("admin_role_id")
                staff_role_id = config.get("staff_role_id")
                user_role_ids = [role.id for role in interaction.user.roles]
                
                if helper_role_id and helper_role_id in user_role_ids:
                    has_helper_role = True
                if admin_role_id and admin_role_id in user_role_ids:
                    is_admin = True
                if staff_role_id and staff_role_id in user_role_ids:
                    is_staff = True
            
            if not (has_helper_role or is_admin or is_staff):
                await interaction.response.send_message("❌ You need the Helper role to join tickets! Contact staff to get the Helper role.", ephemeral=True)
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
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Simple notification message
            await self.ticket_view.channel.send(f"🎉 {interaction.user.mention} joined as a helper! ({len(self.ticket_view.helpers)}/{self.ticket_view.slots} slots filled)")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error joining ticket: {str(e)}", ephemeral=True)

    async def send_staff_notification(self, message: str, guild: discord.Guild):
        """Send notification message only to staff/admin roles"""
        try:
            config = await db.get_server_config(guild.id)
            if not config:
                return
            
            admin_role_id = config.get("admin_role_id")
            staff_role_id = config.get("staff_role_id")
            
            # Get staff/admin members
            staff_mentions = []
            
            if admin_role_id:
                admin_role = guild.get_role(admin_role_id)
                if admin_role:
                    staff_mentions.extend([member.mention for member in admin_role.members if not member.bot])
            
            if staff_role_id:
                staff_role = guild.get_role(staff_role_id)
                if staff_role:
                    staff_mentions.extend([member.mention for member in staff_role.members if not member.bot])
            
            # Remove duplicates
            staff_mentions = list(set(staff_mentions))
            
            if staff_mentions:
                # Send message with staff mentions (only they'll be notified)
                staff_ping = " ".join(staff_mentions[:5])  # Limit to 5 mentions
                await self.channel.send(f"{message} ({staff_ping})", delete_after=30)
            else:
                # No staff configured, send regular message
                await self.channel.send(message, delete_after=30)
                
        except Exception as e:
            print(f"Error sending staff notification: {e}")
            # Fallback to regular message
            await self.channel.send(message, delete_after=30)

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
            # Check permissions - only staff/admin can close
            config = await db.get_server_config(interaction.guild.id)
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
            
            if not (is_admin or is_staff):
                await interaction.response.send_message("❌ Only staff or admins can close tickets!", ephemeral=True)
                return

            # Show confirmation view
            confirmation_view = TicketCloseConfirmationView(self.ticket_view, interaction.user)
            
            embed = discord.Embed(
                title="🔒 Close Ticket Confirmation",
                description=f"Are you sure you want to close this **{self.ticket_view.category}** ticket?",
                color=discord.Color.orange()
            )
            embed.add_field(name="👥 Helpers", value=f"{len(self.ticket_view.helpers)} helpers will be affected", inline=True)
            embed.add_field(name="🏆 Points", value="Choose whether to award points", inline=True)
            embed.add_field(name="⚠️ Warning", value="This action cannot be undone!", inline=False)
            
            await interaction.response.send_message(embed=embed, view=confirmation_view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error accessing close ticket: {str(e)}", ephemeral=True)

class TicketCloseConfirmationView(discord.ui.View):
    def __init__(self, ticket_view: TicketView, staff_member: discord.Member):
        super().__init__(timeout=60)
        self.ticket_view = ticket_view
        self.staff_member = staff_member
        self.value = None

    @discord.ui.button(label="✅ Approve & Give Points", style=discord.ButtonStyle.success)
    async def approve_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get point values for this category
            ticket_cog = interaction.client.get_cog("TicketCommandsCog")
            points = ticket_cog.CATEGORY_POINTS.get(self.ticket_view.category, 0) if ticket_cog else 0
            
            # Award points to helpers
            for helper in self.ticket_view.helpers:
                await db.add_user_points(self.ticket_view.guild_id, helper.id, points)

            # Save transcript
            if isinstance(interaction.channel, discord.TextChannel):
                await self.save_transcript(interaction.channel, self.staff_member)

            # Remove from active tickets
            await db.remove_active_ticket(self.ticket_view.guild_id, self.ticket_view.channel.id)

            # Create closing embed
            embed = discord.Embed(
                title="✅ Ticket Completed Successfully",
                description=f"This **{self.ticket_view.category}** ticket has been completed and approved!",
                color=discord.Color.green()
            )
            embed.add_field(name="👤 Closed By", value=self.staff_member.mention, inline=True)
            embed.add_field(name="👥 Helpers", value=f"{len(self.ticket_view.helpers)} helpers", inline=True)
            embed.add_field(name="🏆 Points Awarded", value=f"{points} points each", inline=True)
            
            if self.ticket_view.helpers:
                helper_mentions = "\n".join([f"• {helper.mention}" for helper in self.ticket_view.helpers])
                embed.add_field(name="🎉 Points Recipients", value=helper_mentions, inline=False)
            
            embed.add_field(name="⏰ Channel Deletion", value="This channel will be deleted in 15 seconds.", inline=False)
            embed.timestamp = discord.utils.utcnow()

            await interaction.response.edit_message(embed=embed, view=None)
            await self.ticket_view.channel.send(embed=embed)
            
            # Delete channel after delay
            await asyncio.sleep(15)
            if isinstance(interaction.channel, discord.TextChannel):
                await interaction.channel.delete(reason=f"Ticket approved and closed by {self.staff_member.display_name}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error approving ticket: {str(e)}", ephemeral=True)

    @discord.ui.button(label="❌ Decline (No Points)", style=discord.ButtonStyle.danger)
    async def decline_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Save transcript but don't award points
            if isinstance(interaction.channel, discord.TextChannel):
                await self.save_transcript(interaction.channel, self.staff_member)

            # Remove from active tickets
            await db.remove_active_ticket(self.ticket_view.guild_id, self.ticket_view.channel.id)

            # Create closing embed
            embed = discord.Embed(
                title="❌ Ticket Declined",
                description=f"This **{self.ticket_view.category}** ticket has been closed without awarding points.",
                color=discord.Color.red()
            )
            embed.add_field(name="👤 Closed By", value=self.staff_member.mention, inline=True)
            embed.add_field(name="👥 Helpers", value=f"{len(self.ticket_view.helpers)} helpers", inline=True)
            embed.add_field(name="🏆 Points Awarded", value="0 points (declined)", inline=True)
            embed.add_field(name="💡 Reason", value="Ticket was declined by staff", inline=False)
            embed.add_field(name="⏰ Channel Deletion", value="This channel will be deleted in 15 seconds.", inline=False)
            embed.timestamp = discord.utils.utcnow()

            await interaction.response.edit_message(embed=embed, view=None)
            await self.ticket_view.channel.send(embed=embed)
            
            # Delete channel after delay
            await asyncio.sleep(15)
            if isinstance(interaction.channel, discord.TextChannel):
                await interaction.channel.delete(reason=f"Ticket declined by {self.staff_member.display_name}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error declining ticket: {str(e)}", ephemeral=True)

    @discord.ui.button(label="🚫 Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🚫 Ticket Close Cancelled",
            description="The ticket remains open.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)

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
            embed.add_field(name="🏆 Rewarded", value="✅ Yes", inline=True)
            
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
            transcript_text += f"Rewarded: Yes\n"
            transcript_text += f"Closed on: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            transcript_text += "\n" + "="*50 + "\n\n"
            transcript_text += "\n".join(messages)
            
            # Create file and send
            file = discord.File(
                fp=io.StringIO(transcript_text),
                filename=f"transcript-{channel.name}.txt"
            )
            
            await transcript_channel.send(embed=embed, file=file)
            
        except Exception as e:
            print(f"Error saving transcript: {e}")
