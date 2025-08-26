import discord
from discord.ext import commands
from discord import app_commands
from database import DatabaseManager

db = DatabaseManager()

class PointsExtraCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mypoints", description="Check your own points")
    async def mypoints(self, interaction: discord.Interaction):
        """Show your own points"""
        try:
            points = await db.get_user_points(interaction.guild.id, interaction.user.id)
            
            embed = discord.Embed(
                title="💰 Your Points",
                description=f"You have **{points}** points.",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
            
            if points == 0:
                embed.add_field(
                    name="💡 How to earn points", 
                    value="Help others with their tickets to earn points!", 
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    @app_commands.command(name="pointsinfo", description="Learn about the points system")
    async def pointsinfo(self, interaction: discord.Interaction):
        """Explain the points system"""
        embed = discord.Embed(
            title="💠 Points System Information",
            description="Learn how the points system works in this server!",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="🎯 How to Earn Points",
            value="• Join tickets as a helper\n• Complete assistance successfully\n• Points are awarded when tickets close",
            inline=False
        )
        
        embed.add_field(
            name="📊 Tracking Your Progress", 
            value="• Use `/mypoints` to see your points\n• Use `/myrank` to see your leaderboard position\n• Use `/leaderboard` to see top helpers",
            inline=False
        )
        
        embed.add_field(
            name="🏆 Point Values",
            value="Different ticket types award different points:\n• Ultra Speaker Express: 8 pts\n• Ultra Gramiel Express: 7 pts\n• 4-Man Ultra Daily: 4 pts\n• 7-Man Ultra Daily: 7 pts\n• Ultra Weekly Express: 12 pts\n• Grim Express: 10 pts\n• Daily Temple Express: 6 pts",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Admin Commands",
            value="Administrators can:\n• Add/remove/set points manually\n• Remove users from leaderboard\n• Reset the entire leaderboard",
            inline=False
        )
        
        embed.set_footer(text="Start helping today to climb the leaderboard!")
        
        await interaction.response.send_message(embed=embed)

# -------------------- LOAD COG --------------------
async def setup(bot):
    await bot.add_cog(PointsExtraCog(bot))
