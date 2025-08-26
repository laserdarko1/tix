import discord
from discord.ext import commands
from discord import app_commands
from database import DatabaseManager

db = DatabaseManager()

class PointsCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mypoints", description="Check your current points")
    async def my_points(self, interaction: discord.Interaction):
        """Check user's own points"""
        try:
            points = await db.get_user_points(interaction.guild.id, interaction.user.id)
            
            embed = discord.Embed(
                title="💰 Your Points",
                description=f"You currently have **{points}** points!",
                color=discord.Color.green()
            )
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            embed.set_footer(text="Keep helping others to earn more points!")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error getting points: {str(e)}", ephemeral=True)

    @app_commands.command(name="points", description="Check points for any user")
    async def check_points(self, interaction: discord.Interaction, user: discord.Member = None):
        """Check points for a specific user"""
        try:
            target_user = user or interaction.user
            points = await db.get_user_points(interaction.guild.id, target_user.id)
            
            if target_user == interaction.user:
                title = "💰 Your Points"
                description = f"You currently have **{points}** points!"
            else:
                title = f"💰 {target_user.display_name}'s Points"
                description = f"{target_user.mention} currently has **{points}** points!"
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.blue()
            )
            embed.set_author(name=target_user.display_name, icon_url=target_user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error getting points: {str(e)}", ephemeral=True)

    @app_commands.command(name="leaderboard", description="View the points leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        """Show the points leaderboard"""
        try:
            all_points = await db.get_all_user_points(interaction.guild.id)
            
            if not all_points:
                embed = discord.Embed(
                    title="🏆 Points Leaderboard",
                    description="No one has points yet! Start helping others to earn points.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Sort by points (descending)
            sorted_users = sorted(all_points.items(), key=lambda x: x[1], reverse=True)
            
            embed = discord.Embed(
                title="🏆 Points Leaderboard",
                description="Top helpers in this server:",
                color=discord.Color.gold()
            )
            
            # Show top 10
            for i, (user_id, points) in enumerate(sorted_users[:10], 1):
                user = interaction.guild.get_member(user_id)
                if user:
                    # Add medal emojis for top 3
                    if i == 1:
                        emoji = "🥇"
                    elif i == 2:
                        emoji = "🥈"
                    elif i == 3:
                        emoji = "🥉"
                    else:
                        emoji = f"{i}."
                    
                    embed.add_field(
                        name=f"{emoji} {user.display_name}",
                        value=f"{points} points",
                        inline=True
                    )
            
            embed.set_footer(text=f"Showing top {min(10, len(sorted_users))} helpers")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error getting leaderboard: {str(e)}", ephemeral=True)

    @app_commands.command(name="myrank", description="Check your leaderboard rank")
    async def my_rank(self, interaction: discord.Interaction):
        """Check user's rank on the leaderboard"""
        try:
            all_points = await db.get_all_user_points(interaction.guild.id)
            user_points = await db.get_user_points(interaction.guild.id, interaction.user.id)
            
            if not all_points:
                embed = discord.Embed(
                    title="📊 Your Rank",
                    description="No leaderboard data available yet!",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Sort by points (descending)
            sorted_users = sorted(all_points.items(), key=lambda x: x[1], reverse=True)
            
            # Find user's rank
            rank = None
            for i, (user_id, points) in enumerate(sorted_users, 1):
                if user_id == interaction.user.id:
                    rank = i
                    break
            
            embed = discord.Embed(
                title="📊 Your Rank",
                color=discord.Color.blue()
            )
            
            if rank:
                embed.description = f"You are ranked **#{rank}** out of {len(sorted_users)} helpers!"
                embed.add_field(name="💰 Your Points", value=f"{user_points} points", inline=True)
                embed.add_field(name="🏆 Your Rank", value=f"#{rank}", inline=True)
                
                # Show points needed for next rank
                if rank > 1:
                    next_user_points = sorted_users[rank-2][1]  # User above them
                    points_needed = next_user_points - user_points + 1
                    embed.add_field(name="⬆️ Next Rank", value=f"{points_needed} more points", inline=True)
            else:
                embed.description = f"You're not on the leaderboard yet. You have {user_points} points."
                embed.add_field(name="💡 Tip", value="Help others with tickets to earn points!", inline=False)
            
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error getting rank: {str(e)}", ephemeral=True)

    @app_commands.command(name="addpoints", description="Add points to a user (staff only)")
    @app_commands.describe(user="The user to add points to", amount="Number of points to add")
    async def add_points(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Add points to a user (staff/admin only)"""
        try:
            # Check permissions
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
                await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
                return
            
            if amount <= 0:
                await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
                return
            
            await db.add_user_points(interaction.guild.id, user.id, amount)
            new_total = await db.get_user_points(interaction.guild.id, user.id)
            
            embed = discord.Embed(
                title="✅ Points Added",
                description=f"Successfully added **{amount}** points to {user.mention}!",
                color=discord.Color.green()
            )
            embed.add_field(name="New Total", value=f"{new_total} points", inline=True)
            embed.add_field(name="Added By", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding points: {str(e)}", ephemeral=True)

    @app_commands.command(name="removepoints", description="Remove points from a user (staff only)")
    @app_commands.describe(user="The user to remove points from", amount="Number of points to remove")
    async def remove_points(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Remove points from a user (staff/admin only)"""
        try:
            # Check permissions
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
                await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
                return
            
            if amount <= 0:
                await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
                return
            
            current_points = await db.get_user_points(interaction.guild.id, user.id)
            new_points = max(0, current_points - amount)
            
            await db.set_user_points(interaction.guild.id, user.id, new_points)
            
            embed = discord.Embed(
                title="✅ Points Removed",
                description=f"Successfully removed **{amount}** points from {user.mention}!",
                color=discord.Color.orange()
            )
            embed.add_field(name="Previous Total", value=f"{current_points} points", inline=True)
            embed.add_field(name="New Total", value=f"{new_points} points", inline=True)
            embed.add_field(name="Removed By", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing points: {str(e)}", ephemeral=True)

    @app_commands.command(name="setpoints", description="Set specific point amount for a user (staff only)")
    @app_commands.describe(user="The user to set points for", amount="Number of points to set")
    async def set_points(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Set specific point amount for a user (staff/admin only)"""
        try:
            # Check permissions
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
                await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
                return
            
            if amount < 0:
                await interaction.response.send_message("❌ Amount cannot be negative!", ephemeral=True)
                return
            
            old_points = await db.get_user_points(interaction.guild.id, user.id)
            await db.set_user_points(interaction.guild.id, user.id, amount)
            
            embed = discord.Embed(
                title="✅ Points Set",
                description=f"Successfully set {user.mention}'s points to **{amount}**!",
                color=discord.Color.blue()
            )
            embed.add_field(name="Previous Total", value=f"{old_points} points", inline=True)
            embed.add_field(name="New Total", value=f"{amount} points", inline=True)
            embed.add_field(name="Set By", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error setting points: {str(e)}", ephemeral=True)

    @app_commands.command(name="removeuser", description="Remove user from leaderboard (staff only)")
    @app_commands.describe(user="The user to remove from leaderboard")
    async def remove_user(self, interaction: discord.Interaction, user: discord.Member):
        """Remove user from leaderboard (staff/admin only)"""
        try:
            # Check permissions
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
                await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
                return
            
            old_points = await db.get_user_points(interaction.guild.id, user.id)
            await db.remove_user(interaction.guild.id, user.id)
            
            embed = discord.Embed(
                title="✅ User Removed",
                description=f"Successfully removed {user.mention} from the leaderboard!",
                color=discord.Color.red()
            )
            embed.add_field(name="Points Removed", value=f"{old_points} points", inline=True)
            embed.add_field(name="Removed By", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user: {str(e)}", ephemeral=True)

    @app_commands.command(name="resetleaderboard", description="Reset entire leaderboard (admin only)")
    async def reset_leaderboard(self, interaction: discord.Interaction):
        """Reset entire leaderboard (admin only)"""
        try:
            # Check admin permissions
            is_admin = interaction.user.guild_permissions.administrator
            config = await db.get_server_config(interaction.guild.id)
            
            if config:
                admin_role_id = config.get("admin_role_id")
                user_role_ids = [role.id for role in interaction.user.roles]
                
                if admin_role_id and admin_role_id in user_role_ids:
                    is_admin = True
            
            if not is_admin:
                await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
                return
            
            await db.clear_all_points(interaction.guild.id)
            
            embed = discord.Embed(
                title="✅ Leaderboard Reset",
                description="The entire points leaderboard has been reset!",
                color=discord.Color.red()
            )
            embed.add_field(name="Reset By", value=interaction.user.mention, inline=True)
            embed.add_field(name="⚠️ Warning", value="This action cannot be undone!", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error resetting leaderboard: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PointsCommandsCog(bot))
