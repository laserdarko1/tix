import discord
from discord.ui import Modal, TextInput
from discord import Interaction

class TicketModal(Modal):
    def __init__(self, category: str, guild_id: int):
        super().__init__(title=f"Create {category} Ticket")
        self.category = category
        self.guild_id = guild_id

        # Modal fields
        self.in_game_name = TextInput(
            label="In-game Name",
            placeholder="Enter your character/account name",
            style=discord.TextStyle.short,
            max_length=100,
            required=True
        )
        self.add_item(self.in_game_name)

        self.server_name = TextInput(
            label="Server Name", 
            placeholder="Which server are you playing on?",
            style=discord.TextStyle.short,
            max_length=100,
            required=True
        )
        self.add_item(self.server_name)

        self.room_number = TextInput(
            label="Room Number",
            placeholder="Enter the room/channel number if applicable",
            style=discord.TextStyle.short,
            max_length=50,
            required=True
        )
        self.add_item(self.room_number)

        self.additional_info = TextInput(
            label="Additional Information (Optional)",
            placeholder="Any special requirements, preferred time, or other details...",
            style=discord.TextStyle.long,
            max_length=500,
            required=False
        )
        self.add_item(self.additional_info)

    async def on_submit(self, interaction: Interaction):
        try:
            # Defer the response since ticket creation takes time
            await interaction.response.defer(ephemeral=True)
            
            # Get the ticket commands cog and use its create_ticket method
            ticket_cog = interaction.client.get_cog("TicketCommandsCog")
            if not ticket_cog:
                await interaction.followup.send("❌ Ticket system not available! Please try again later.", ephemeral=True)
                return

            # Prepare answers dictionary
            answers = {
                "In-game Name": self.in_game_name.value,
                "Server Name": self.server_name.value, 
                "Room Number": self.room_number.value,
                "Additional Info": self.additional_info.value if self.additional_info.value else None
            }

            # Create the ticket using the ticket cog's method
            await ticket_cog.create_ticket(interaction, self.category, answers)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error submitting ticket: {str(e)}", ephemeral=True)

    async def on_error(self, interaction: Interaction, error: Exception):
        await interaction.response.send_message(f"❌ An error occurred while creating your ticket: {str(error)}", ephemeral=True)
