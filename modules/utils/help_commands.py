import discord
from discord.ext import commands
from discord import app_commands
from database import DatabaseManager

db = DatabaseManager()

class HelpCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all bot commands and help information")
    async def help_command(self, interaction: discord.Interaction):
        """Show all bot commands and help"""
        try:
            # Check if user has admin/staff permissions
            user = interaction.user
            guild = interaction.guild

            # Check permissions
            config = await db.get_server_config(guild.id)
            is_admin = user.guild_permissions.administrator
            is_staff = False
            
            if config:
                admin_role_id = config.get("admin_role_id")
                staff_role_id = config.get("staff_role_id")
                user_role_ids = [role.id for role in user.roles]
                
                if admin_role_id and admin_role_id in user_role_ids:
                    is_admin = True
                if staff_role_id and staff_role_id in user_role_ids:
                    is_staff = True

            # Create main help embed
            embed = discord.Embed(
                title="🤖 Bot Commands & Help",
                description="Welcome to the ticket assistance bot! Here are all available commands organized by category.",
                color=discord.Color.blurple()
            )

            # General User Commands
            user_commands = (
                "`/help` - Show this help message\n"
                "`/mypoints` - Check your own points\n"
                "`/points [@user]` - Check points for any user\n"
                "`/myrank` - See your leaderboard position\n"
                "`/leaderboard` - View the top helpers\n"
                "`/pointsinfo` - Learn about the points system\n"
                "`/ticketcount` - View ticket statistics"
            )
            embed.add_field(name="👤 General Commands", value=user_commands, inline=False)

            # Ticket Commands
            ticket_commands = (
                "🎫 **Creating Tickets:**\n"
                "Use the ticket panel to create assistance requests\n\n"
                "🙋 **Helping Others:**\n"
                "• Join tickets to help other players\n"
                "• Leave tickets if you can't continue\n"
                "• Earn points when tickets are completed"
            )
            embed.add_field(name="🎫 Ticket System", value=ticket_commands, inline=False)

            # Information Commands
            info_commands = (
                "`/rrules` - View rules for requesters\n"
                "`/hrules` - View rules for helpers\n"
                "`/proof` - View proof submission guidelines"
            )
            embed.add_field(name="📋 Information Commands", value=info_commands, inline=False)

            # Staff/Admin Commands (only show to staff/admin)
            if is_admin or is_staff:
                staff_commands = ""
                
                if is_admin or is_staff:
                    staff_commands += (
                        "`/addpoints @user amount` - Add points to a user\n"
                        "`/removepoints @user amount` - Remove points from a user\n"
                        "`/setpoints @user amount` - Set specific point amount\n"
                        "`/removeuser @user` - Remove user from leaderboard\n"
                    )
                
                if is_admin:
                    staff_commands += (
                        "`/resetleaderboard` - Reset entire leaderboard\n"
                        "`/createpanel` - Create ticket selection panel\n"
                        "`/ticketcount` - View detailed ticket statistics\n"
                        "`/setup` - Configure server settings\n"
                        "`/setupcommands` - Configure custom commands\n"
                        "`/resetsetup` - Reset all configuration"
                    )
                
                embed.add_field(name="🛡️ Staff/Admin Commands", value=staff_commands, inline=False)

            # Point Values Information
            points_info = (
                "**Ticket Point Values:**\n"
                "🏆 Ultra Speaker Express: 8 points\n"
                "🏆 Ultra Gramiel Express: 7 points\n"
                "🏆 4-Man Ultra Daily Express: 4 points\n"
                "🏆 7-Man Ultra Daily Express: 7 points\n"
                "🏆 Ultra Weekly Express: 12 points\n"
                "🏆 Grim Express: 10 points\n"
                "🏆 Daily Temple Express: 6 points"
            )
            embed.add_field(name="🏆 Point Values", value=points_info, inline=False)

            # Usage Tips
            tips = (
                "💡 **Tips for Success:**\n"
                "• Be patient when waiting for helpers\n"
                "• Provide clear information in tickets\n"
                "• Follow server rules and be respectful\n"
                "• Help others to earn points and climb the leaderboard\n"
                "• Check `/pointsinfo` for more details about earning points\n"
                "• Opening tickets may also award points!"
            )
            embed.add_field(name="💡 Usage Tips", value=tips, inline=False)

            # Footer
            embed.set_footer(text="Need more help? Contact a member of the staff team!")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error displaying help: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCommandsCog(bot))
