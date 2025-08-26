import discord
from discord.ext import commands
from discord import app_commands
from database import DatabaseManager

db = DatabaseManager()

class PointsExtraCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pointsinfo", description="Learn about the points system")
    async def points_info(self, interaction: discord.Interaction):
        """Show information about the points system"""
        try:
            # Get server configuration for opening points
            config = await db.get_server_config(interaction.guild.id)
            opening_points = config.get("opening_points", 0) if config else 0
            
            embed = discord.Embed(
                title="🏆 Points System Information",
                description="Learn how to earn points and climb the leaderboard!",
                color=discord.Color.gold()
            )
            
            # How to earn points
            earning_text = (
                "🙋 **Helping Others:**\n"
                "Join tickets and help other players complete their goals. "
                "You earn points when the ticket is successfully closed.\n\n"
            )
            
            if opening_points > 0:
                earning_text += f"🎫 **Opening Tickets:**\n"
                earning_text += f"Earn {opening_points} points just for opening a ticket!\n\n"
            
            earning_text += (
                "📈 **Point Values per Ticket:**\n"
                "Different ticket types award different point amounts based on difficulty."
            )
            
            embed.add_field(name="💰 How to Earn Points", value=earning_text, inline=False)
            
            # Point values
            values_text = (
                "🏆 Ultra Speaker Express: **8 points**\n"
                "🏆 Ultra Gramiel Express: **7 points**\n" 
                "🏆 4-Man Ultra Daily Express: **4 points**\n"
                "🏆 7-Man Ultra Daily Express: **7 points**\n"
                "🏆 Ultra Weekly Express: **12 points**\n"
                "🏆 Grim Express: **10 points**\n"
                "🏆 Daily Temple Express: **6 points**"
            )
            embed.add_field(name="📊 Point Values", value=values_text, inline=False)
            
            # Tips for success
            tips_text = (
                "• Join tickets that match your skill level\n"
                "• Be reliable and complete tickets you join\n"
                "• Help new players learn the content\n"
                "• Use `/leaderboard` to see top helpers\n"
                "• Check `/myrank` to track your progress"
            )
            
            if opening_points > 0:
                tips_text += f"\n• Create tickets when you need help (earn {opening_points} points!)"
            
            embed.add_field(name="💡 Tips for Success", value=tips_text, inline=False)
            
            # Commands
            commands_text = (
                "`/mypoints` - Check your current points\n"
                "`/points @user` - Check anyone's points\n"
                "`/leaderboard` - View top helpers\n"
                "`/myrank` - See your rank position"
            )
            embed.add_field(name="📋 Related Commands", value=commands_text, inline=False)
            
            embed.set_footer(text="Points are server-specific and reset only by administrators")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error displaying points info: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PointsExtraCog(bot))
