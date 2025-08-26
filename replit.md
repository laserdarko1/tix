# Overview

This is a Discord bot designed for game assistance servers, specifically focused on managing ticket requests and help systems. The bot provides a comprehensive points-based reward system where users earn points by helping others complete various game challenges through a structured ticket system. It features different ticket categories with varying difficulty levels and point rewards, user role management, custom command configuration, and server setup utilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Components

**Discord Bot Framework**: Built using discord.py with slash commands (app_commands) as the primary interface. The bot uses a cog-based modular architecture with separate modules for different functionalities (points, setup, tickets, utils).

**Database Layer**: Uses SQLite with aiosqlite for asynchronous database operations. The DatabaseManager class handles all database interactions with tables for user points, server configuration, and custom commands. The database supports multi-guild operations with guild_id as a key identifier.

**Modular Structure**: The codebase is organized into distinct modules:
- `modules/points/`: Handles point tracking, leaderboards, and point-related commands
- `modules/setup/`: Manages server configuration and role/channel setup
- `modules/tickets/`: Manages ticket creation, helper assignment, and ticket lifecycle
- `modules/utils/`: Contains utility functions like help commands

**Web Server Integration**: Includes a Flask web server for health checks and monitoring, running on a separate daemon thread to ensure the bot remains responsive.

## Data Architecture

**Multi-Guild Support**: All database tables include guild_id to support multiple Discord servers with isolated configurations and data.

**Points System**: Tracks user points per guild with different point values for various ticket categories. Supports both earning points through helping and optional opening points for ticket creation.

**Role-Based Permissions**: Configurable role system with admin, staff, helper, viewer, blocked, and reward roles that control access to different bot features.

**Custom Commands**: Flexible system for server administrators to configure custom informational commands with optional image support.

## User Interface Design

**Interactive Elements**: Heavy use of Discord UI components including modals for data input, select menus for ticket category selection, and buttons for ticket management actions.

**Embed-Rich Responses**: All bot responses use Discord embeds for better visual presentation and consistent formatting across different command types.

**Ephemeral Messaging**: Strategic use of ephemeral responses for sensitive operations like setup commands and personal point checks to reduce channel clutter.

# External Dependencies

**Discord API**: Primary integration through discord.py library for all bot functionality, user interactions, and guild management.

**SQLite Database**: Local file-based database storage using aiosqlite for asynchronous operations. Database file location is configurable via environment variables.

**Flask Web Framework**: Lightweight web server for health monitoring and external service integration, accessible via HTTP endpoints.

**Environment Configuration**: Uses python-dotenv for secure configuration management, particularly for the Discord bot token and database path settings.

**Logging System**: Built-in Python logging for debugging and monitoring bot operations across all modules.