import discord
from discord.ext import commands
from discord import app_commands
from database import DatabaseManager

db = DatabaseManager()

class TicketStatisticsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticketcount", description="View ticket statistics and counts")
    async def ticket_count(self, interaction: discord.Interaction):
        """Show ticket counts and statistics"""
        try:
            # Get all ticket counts for this guild
            active_tickets = await db.get_active_tickets(interaction.guild.id)
            ticket_counters = await db.get_ticket_counters(interaction.guild.id)
            
            embed = discord.Embed(
                title="🎫 Ticket Statistics",
                description="Here are the current ticket counts and statistics for this server.",
                color=discord.Color.blue()
            )
            
            # Categories with their point values
            categories = {
                "Ultra Speaker Express": 8,
                "Ultra Gramiel Express": 7,
                "4-Man Ultra Daily Express": 4,
                "7-Man Ultra Daily Express": 7,
                "Ultra Weekly Express": 12,
                "Grim Express": 10,
                "Daily Temple Express": 6
            }
            
            # Count active tickets by category
            active_by_category = {}
            for ticket in active_tickets:
                category = ticket.get('category', 'Unknown')
                active_by_category[category] = active_by_category.get(category, 0) + 1
            
            # Create statistics display
            stats_text = ""
            total_created = 0
            total_active = 0
            
            for category, points in categories.items():
                created = ticket_counters.get(category, 0)
                active = active_by_category.get(category, 0)
                total_created += created
                total_active += active
                
                stats_text += f"**{category}**\n"
                stats_text += f"  • Total Created: {created}\n"
                stats_text += f"  • Currently Active: {active}\n"
                stats_text += f"  • Point Value: {points} pts\n\n"
            
            embed.add_field(name="📊 Ticket Breakdown", value=stats_text, inline=False)
            
            # Summary statistics
            summary_text = f"**Total Tickets Created:** {total_created}\n"
            summary_text += f"**Currently Active:** {total_active}\n"
            summary_text += f"**Completed Tickets:** {total_created - total_active}"
            
            embed.add_field(name="📈 Summary", value=summary_text, inline=True)
            
            # Most popular category
            if ticket_counters:
                popular_category = max(ticket_counters.items(), key=lambda x: x[1])
                embed.add_field(
                    name="🔥 Most Popular", 
                    value=f"{popular_category[0]}\n({popular_category[1]} tickets)", 
                    inline=True
                )
            
            embed.set_footer(text="Statistics updated in real-time")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error fetching ticket statistics: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketStatisticsCog(bot))