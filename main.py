import discord
from discord.ext import commands
from discord import app_commands
import quest_manager as qm

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = False

bot = commands.Bot(command_prefix="!", intents=intents)

# Sync slash commands


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")


# ---------------- SETUP ----------------
@bot.tree.command(name="setup", description="Configure quest role & log channel")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, role: discord.Role, log_channel: discord.TextChannel):
    config = qm.load_config()
    config["guild_id"] = interaction.guild.id
    config["quest_role_id"] = role.id
    config["log_channel_id"] = log_channel.id
    qm.save_config(config)

    await interaction.response.send_message(
        f"✅ Setup complete!\nQuest role: {role.mention}\nLog channel: {log_channel.mention}",
        ephemeral=True
    )


# ---------------- QUEST CREATION ----------------
@bot.tree.command(name="quest", description="Create a new quest")
@app_commands.describe(
    title="Title of the quest",
    description="Description of the quest",
    reward="Reward for completing",
    deadline="Deadline (e.g. 24h, 3 days)"
)
async def quest(interaction: discord.Interaction, title: str, description: str, reward: str, deadline: str):
    config = qm.load_config()
    quest_data = qm.create_quest(title, description, reward, deadline)
    quest_role = interaction.guild.get_role(config["quest_role_id"])

    # Create embed
    embed = discord.Embed(
        title=f"📜 Quest: {quest_data['title']}",
        description=quest_data["description"],
        color=discord.Color.gold()
    )
    embed.add_field(name="💰 Reward", value=quest_data["reward"], inline=True)
    embed.add_field(name="⏳ Deadline",
                    value=quest_data["deadline"], inline=True)
    embed.set_footer(text=f"Contract ID: {quest_data['contract_id']}")

    # Buttons
    view = QuestButtons(quest_data['contract_id'])

    await interaction.response.send_message(
        f"{quest_role.mention} A new quest has been posted!",
        embed=embed,
        view=view
    )


# Staff-only command to post a long, explanatory guide in a channel
STAFF_ROLE_ID = 1120278949679861834  # Replace with your staff role ID


def is_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        return STAFF_ROLE_ID in [role.id for role in interaction.user.roles]
    return app_commands.check(predicate)


@bot.tree.command(name="post_staff_guide", description="Post the full staff guide in a specified channel (staff only)")
@is_staff()
async def post_staff_guide(interaction: discord.Interaction, channel: discord.TextChannel):
    embed = discord.Embed(
        title="📜 Quest Bot Staff Guide & Workflow",
        color=discord.Color.green()
    )

    embed.add_field(
        name="1️⃣ Overview",
        value=(
            "Welcome staff members! This guide explains your responsibilities in the Quest Bot system.\n\n"
            "The Quest Bot posts quests, allows users to accept/decline them, and logs all interactions.\n"
            "**Only admins create quests and assign roles.**\n"
            "Staff’s role is to coordinate with the **message tracker** to ensure user progress is correctly updated."
        ),
        inline=False
    )

    embed.add_field(
        name="2️⃣ Admins vs Staff",
        value=(
            "**Admins:**\n"
            "• Use `/setup` to configure the quest role and log channel.\n"
            "• Create quests via `/quest_create` with title, description, reward, and deadline.\n\n"
            "**Staff:**\n"
            "• Do **not** create quests.\n"
            "• Update quest targets in the **message tracker** after an admin posts a quest.\n"
            "• Monitor users to ensure progress is tracked.\n"
            "• Assist users who face issues updating the tracker."
        ),
        inline=False
    )

    embed.add_field(
        name="3️⃣ User Interaction",
        value=(
            "When a quest is posted:\n"
            "• Users see an embed with all details (title, description, reward, deadline, contract ID).\n"
            "• Users interact via buttons: **Accept (✅)** or **Decline (❌)**.\n"
            "• Once a user accepts, they cannot decline, and vice versa.\n"
            "• Users receive a DM confirming their action.\n"
            "**Your role:** Monitor the log channel for Accept/Decline actions and ensure users update the message tracker."
        ),
        inline=False
    )

    embed.add_field(
        name="4️⃣ Coordinating with the Message Tracker",
        value=(
            "• Update the target or goal in the message tracker whenever a new quest is posted by admins.\n"
            "• Users themselves update progress in the tracker.\n"
            "• Verify that the tracker’s targets match the quest details.\n"
            "• Encourage consistent updates to maintain accurate records."
        ),
        inline=False
    )

    embed.add_field(
        name="5️⃣ Monitoring & Best Practices",
        value=(
            "• All Accept/Decline actions are logged in the configured log channel.\n"
            "• Use the logs to track participation and identify inactive users.\n"
            "• Ensure consistency between the Quest Bot and the message tracker.\n"
            "• Staff’s main responsibility is **accuracy, consistency, and assisting users**."
        ),
        inline=False
    )

    embed.set_footer(text="Quest Bot • Staff Guide • Use responsibly")

    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Staff guide posted in {channel.mention}", ephemeral=True)


# ---------------- BUTTONS ----------------
class QuestButtons(discord.ui.View):
    def __init__(self, contract_id):
        super().__init__(timeout=None)
        self.contract_id = contract_id

    async def log_action(self, guild, user, action, quest_title):
        config = qm.load_config()
        log_channel_id = config.get("log_channel_id")
        if not log_channel_id:
            return
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(
                f"📝 **{user}** ({user.id}) {action} quest **{quest_title}** (Contract {self.contract_id})"
            )

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        quests = qm.load_quests()
        quest = quests.get(self.contract_id)

        if interaction.user.id in quest["accepted"]:
            await interaction.response.send_message("You already accepted this quest!", ephemeral=True)
            return
        if interaction.user.id in quest["declined"]:
            await interaction.response.send_message("You declined this quest. You cannot accept it now.", ephemeral=True)
            return

        # Accepting locks decline
        quest["accepted"].append(interaction.user.id)
        qm.save_quests(quests)

        # Disable Decline button
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == "❌ Decline":
                child.disabled = True
        await interaction.message.edit(view=self)

        await interaction.user.send(f"✅ You accepted quest **{quest['title']}** (Contract {self.contract_id})")
        await interaction.response.send_message("Quest accepted!", ephemeral=True)
        await self.log_action(interaction.guild, interaction.user, "accepted", quest["title"])

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        quests = qm.load_quests()
        quest = quests.get(self.contract_id)

        if interaction.user.id in quest["declined"]:
            await interaction.response.send_message("You already declined this quest!", ephemeral=True)
            return
        if interaction.user.id in quest["accepted"]:
            await interaction.response.send_message("You accepted this quest. You cannot decline it now.", ephemeral=True)
            return

        quest["declined"].append(interaction.user.id)
        qm.save_quests(quests)

        # Disable Accept button
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label == "✅ Accept":
                child.disabled = True
        await interaction.message.edit(view=self)

        await interaction.response.send_message("You declined the quest.", ephemeral=True)
        await self.log_action(interaction.guild, interaction.user, "declined", quest["title"])


bot.run("bottoken")
