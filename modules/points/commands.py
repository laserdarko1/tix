import discord
from discord.ext import commands
from discord import app_commands, ui
from database import DatabaseManager

db = DatabaseManager()

class PointsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== POINTS COMMAND ====================
    @app_commands.command(name="points", description="Check points for yourself or another user")
    @app_commands.describe(member="The user to check points for (optional)")
    async def points(self, interaction: discord.Interaction, member: discord.Member = None):
        """Check points for yourself or another user"""
        try:
            member = member or interaction.user
            points = await db.get_user_points(interaction.guild.id, member.id)
            
            embed = discord.Embed(
                title="💰 Points Check",
                description=f"{member.display_name} has **{points}** points.",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    # ==================== LEADERBOARD COMMAND ====================
    @app_commands.command(name="leaderboard", description="Show the top 10 users on the leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        """Show the top 10 users on the leaderboard"""
        try:
            all_points = await db.get_all_user_points(interaction.guild.id)
            if not all_points:
                embed = discord.Embed(
                    title="🏆 Leaderboard",
                    description="No points recorded yet. Start helping to earn points!",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return

            sorted_points = sorted(all_points.items(), key=lambda x: x[1], reverse=True)
            
            embed = discord.Embed(
                title="🏆 Top Helpers Leaderboard",
                description="Here are our amazing helpers ranked by their contributions!",
                color=discord.Color.gold()
            )
            
            # Create a beautiful leaderboard display
            leaderboard_text = ""
            for i, (user_id, points) in enumerate(sorted_points[:10], start=1):
                member = interaction.guild.get_member(user_id)
                name = member.display_name if member else "Unknown User"
                
                # Add special formatting for top 3
                if i == 1:
                    leaderboard_text += f"🥇 **#{i} {name}** — `{points:,} points`\n"
                elif i == 2:
                    leaderboard_text += f"🥈 **#{i} {name}** — `{points:,} points`\n"
                elif i == 3:
                    leaderboard_text += f"🥉 **#{i} {name}** — `{points:,} points`\n"
                else:
                    leaderboard_text += f"🏅 **#{i} {name}** — `{points:,} points`\n"
            
            embed.add_field(name="📊 Top Contributors", value=leaderboard_text, inline=False)
            
            # Add some stats
            total_helpers = len(sorted_points)
            total_points = sum(points for _, points in sorted_points)
            
            stats_text = f"**Total Helpers:** {total_helpers}\n**Total Points Earned:** {total_points:,}\n**Average Points:** {total_points // total_helpers if total_helpers > 0 else 0:,}"
            embed.add_field(name="📈 Server Stats", value=stats_text, inline=True)
            
            # Add motivational message
            if len(sorted_points) >= 3:
                top_3_avg = sum(points for _, points in sorted_points[:3]) // 3
                embed.add_field(name="🎯 Challenge", value=f"Top 3 average: `{top_3_avg:,} points`\nHelp more tickets to climb higher!", inline=True)
            
            embed.set_footer(text=f"🏆 Showing top {min(len(sorted_points), 10)} out of {len(sorted_points)} helpers")
            embed.timestamp = discord.utils.utcnow()

            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    # ==================== MY RANK COMMAND ====================
    @app_commands.command(name="myrank", description="Show your current rank in the leaderboard")
    async def myrank(self, interaction: discord.Interaction):
        """Show your current rank in the leaderboard"""
        try:
            all_points = await db.get_all_user_points(interaction.guild.id)
            sorted_points = sorted(all_points.items(), key=lambda x: x[1], reverse=True)
            
            user_points = await db.get_user_points(interaction.guild.id, interaction.user.id)
            
            embed = discord.Embed(color=discord.Color.blue())
            embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
            
            for i, (user_id, points) in enumerate(sorted_points, start=1):
                if user_id == interaction.user.id:
                    embed.title = f"📊 Your Rank: #{i}"
                    embed.description = f"You have **{points:,}** points and are ranked **#{i}** out of {len(sorted_points)} helpers."
                    embed.add_field(name="🎯 Your Position", value=f"Rank #{i}", inline=True)
                    embed.add_field(name="💰 Your Points", value=f"{points:,} points", inline=True)
                    embed.add_field(name="👥 Total Helpers", value=f"{len(sorted_points)} helpers", inline=True)
                    
                    # Add progress info
                    if i > 1:
                        next_rank_points = sorted_points[i-2][1]
                        points_needed = next_rank_points - points + 1
                        embed.add_field(name="📈 Next Rank", value=f"{points_needed:,} points needed", inline=True)
                    else:
                        embed.add_field(name="👑 Status", value="You're #1!", inline=True)
                    
                    await interaction.response.send_message(embed=embed)
                    return
            
            embed.title = "📊 Your Rank: Unranked"
            embed.description = f"You have **{user_points:,}** points and are not yet on the leaderboard."
            embed.add_field(name="💡 Tip", value="Start helping with tickets to earn points and join the leaderboard!", inline=False)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    # ==================== ADD POINTS (ADMIN ONLY) ====================
    @app_commands.command(name="addpoints", description="Add points to a user (admin only)")
    @app_commands.describe(member="The user to add points to", amount="Amount of points to add")
    @app_commands.default_permissions(administrator=True)
    async def addpoints(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """Add points to a user (admin only)"""
        try:
            if amount <= 0:
                await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
                return
                
            await db.add_user_points(interaction.guild.id, member.id, amount)
            new_total = await db.get_user_points(interaction.guild.id, member.id)
            
            embed = discord.Embed(
                title="✅ Points Added",
                description=f"Added **{amount:,}** points to {member.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="New Total", value=f"{new_total:,} points", inline=True)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    # ==================== REMOVE POINTS (ADMIN ONLY) ====================
    @app_commands.command(name="removepoints", description="Remove points from a user (admin only)")
    @app_commands.describe(member="The user to remove points from", amount="Amount of points to remove")
    @app_commands.default_permissions(administrator=True)
    async def removepoints(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """Remove points from a user (admin only)"""
        try:
            if amount <= 0:
                await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
                return
                
            current = await db.get_user_points(interaction.guild.id, member.id)
            new_total = max(current - amount, 0)
            await db.set_user_points(interaction.guild.id, member.id, new_total)
            
            embed = discord.Embed(
                title="✅ Points Removed",
                description=f"Removed **{amount:,}** points from {member.mention}",
                color=discord.Color.orange()
            )
            embed.add_field(name="Previous Total", value=f"{current:,} points", inline=True)
            embed.add_field(name="New Total", value=f"{new_total:,} points", inline=True)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    # ==================== SET POINTS (ADMIN ONLY) ====================
    @app_commands.command(name="setpoints", description="Set points for a user (admin only)")
    @app_commands.describe(member="The user to set points for", amount="Amount of points to set")
    @app_commands.default_permissions(administrator=True)
    async def setpoints(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        """Set points for a user (admin only)"""
        try:
            if amount < 0:
                await interaction.response.send_message("❌ Amount cannot be negative!", ephemeral=True)
                return
                
            await db.set_user_points(interaction.guild.id, member.id, amount)
            
            embed = discord.Embed(
                title="✅ Points Set",
                description=f"Set {member.mention}'s points to **{amount:,}**",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    # ==================== REMOVE USER (ADMIN ONLY) ====================
    @app_commands.command(name="removeuser", description="Remove a specific user from the leaderboard")
    @app_commands.describe(member="The user to remove from leaderboard")
    @app_commands.default_permissions(administrator=True)
    async def removeuser(self, interaction: discord.Interaction, member: discord.Member):
        """Remove a specific user from the leaderboard"""
        try:
            points = await db.get_user_points(interaction.guild.id, member.id)
            if points == 0:
                await interaction.response.send_message(f"❌ {member.display_name} is not on the leaderboard!", ephemeral=True)
                return
                
            await db.remove_user(interaction.guild.id, member.id)
            
            embed = discord.Embed(
                title="✅ User Removed",
                description=f"{member.mention} has been removed from the leaderboard",
                color=discord.Color.red()
            )
            embed.add_field(name="Previous Points", value=f"{points:,} points", inline=True)
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    # ==================== RESET LEADERBOARD (ADMIN ONLY) ====================
    @app_commands.command(name="resetleaderboard", description="Reset the leaderboard with confirmation")
    @app_commands.default_permissions(administrator=True)
    async def resetleaderboard(self, interaction: discord.Interaction):
        """Reset the leaderboard with confirmation"""
        
        class ConfirmResetView(ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.value = None

            @ui.button(label="✅ Confirm Reset", style=discord.ButtonStyle.danger)
            async def confirm(self, button_interaction: discord.Interaction, button: ui.Button):
                try:
                    await db.clear_all_points(interaction.guild.id)
                    
                    embed = discord.Embed(
                        title="✅ Leaderboard Reset",
                        description="The leaderboard has been completely reset!",
                        color=discord.Color.green()
                    )
                    
                    await button_interaction.response.edit_message(embed=embed, view=None)
                    self.value = True
                    self.stop()
                except Exception as e:
                    await button_interaction.response.send_message(f"❌ Error resetting leaderboard: {str(e)}", ephemeral=True)

            @ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, button_interaction: discord.Interaction, button: ui.Button):
                embed = discord.Embed(
                    title="❌ Reset Cancelled",
                    description="Leaderboard reset has been cancelled.",
                    color=discord.Color.blue()
                )
                await button_interaction.response.edit_message(embed=embed, view=None)
                self.value = False
                self.stop()

            async def on_timeout(self):
                embed = discord.Embed(
                    title="⏰ Timeout",
                    description="Reset confirmation timed out. Leaderboard was not reset.",
                    color=discord.Color.orange()
                )
                await interaction.edit_original_response(embed=embed, view=None)

        embed = discord.Embed(
            title="⚠️ Confirm Leaderboard Reset",
            description="Are you sure you want to reset the entire leaderboard? This action cannot be undone!",
            color=discord.Color.red()
        )
        
        view = ConfirmResetView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==================== LOAD COG ====================
async def setup(bot):
    await bot.add_cog(PointsCog(bot))
