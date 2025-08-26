import discord
from discord.ext import commands
from discord import app_commands
from database import DatabaseManager

db = DatabaseManager()

class SetupResetCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="resetsetup", description="Reset all server configuration (admin only)")
    @app_commands.default_permissions(administrator=True)
    async def resetsetup(self, interaction: discord.Interaction):
        """Reset all server configuration"""
        try:
            await db.update_server_config(interaction.guild.id,
                                          admin_role_id=None,
                                          staff_role_id=None,
                                          helper_role_id=None,
                                          viewer_role_id=None,
                                          blocked_role_id=None,
                                          reward_role_id=None,
                                          ticket_category_id=None,
                                          transcript_channel_id=None)
            
            embed = discord.Embed(
                title="✅ Setup Reset Complete",
                description="All server configuration has been reset to defaults.",
                color=discord.Color.green()
            )
            embed.add_field(
                name="🔄 What was reset:",
                value="• All role configurations\n• All channel configurations\n• Server settings",
                inline=False
            )
            embed.add_field(
                name="📝 Next Steps:",
                value="Use `/setup` to reconfigure your server settings.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error resetting setup: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetupResetCog(bot))
