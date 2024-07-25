import discord
from discord.ext import commands
from discord.ui import Select, View

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Dicionário que mapeia emojis para funções
emoji_role_mapping = {
    "👑": "MAIN TANK",
    "🛡️": "OFF TANK",
    "🍀": "TANK HEALER",
    "🌸": "PT HEALER",
    "🔮": "SUPORTE",
    "⚔️": "DPS",
    "❌": "REMOVE",
}

# Armazenar a mensagem enviada para edição futura
template_message = None
user_roles = {
    "MAIN TANK": None,
    "OFF TANK": None,
    "TANK HEALER": None,
    "PT HEALER": None,
    "SUPORTE": None,
    "DPS 1": None,
    "DPS 2": None,
    "DPS 3": None,
    "DPS 4": None,
    "DPS 5": None,
}

user_queue = {
    "MAIN TANK": [],
    "OFF TANK": [],
    "TANK HEALER": [],
    "PT HEALER": [],
    "SUPORTE": [],
}

selected_weapons = set()

weapon_options = {
    "SUPORTE": [
        discord.SelectOption(label="Enigmático"),
        discord.SelectOption(label="Para-tempo"),
        discord.SelectOption(label="Execrado"),
    ],
    "DPS": [
        discord.SelectOption(label="Entalhada"),
        discord.SelectOption(label="Aclaradas"),
        discord.SelectOption(label="Cria-reis"),
        discord.SelectOption(label="Quebra-reinos"),
        discord.SelectOption(label="Segadeira"),
        discord.SelectOption(label="Prisma"),
        discord.SelectOption(label="Cravadas"),
        discord.SelectOption(label="Infernais"),
        discord.SelectOption(label="Caça-espíritos"),
        discord.SelectOption(label="Astral"),
        discord.SelectOption(label="Archa"),
    ],
}

build_options = {
    "T7": "EQUIVALENTE A T7 + VEADO GIGANTE + 10 ENERGIAS + 5 RESIST + 3 FOODS",
    "T8": "EQUIVALENTE A T8 + VEADO GIGANTE + 10 ENERGIAS + 5 RESIST + 3 FOODS",
    "T7 ARMA + EQUIPS T8": "ARMA T7 + EQUIPS T8 + VEADO GIGANTE + 10 ENERGIAS + 5 RESIST + 3 FOODS",
}


class BuildSelect(Select):
    def __init__(self, ctx):
        options = [
            discord.SelectOption(label="T7"),
            discord.SelectOption(label="T8"),
            discord.SelectOption(label="T7 ARMA + EQUIPS T8"),
        ]
        super().__init__(
            placeholder="Escolha a build",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        selected_build = self.values[0]
        build_text = build_options[selected_build]
        await send_template(self.ctx, build_text)
        await interaction.message.delete()


class BuildSelectView(View):
    def __init__(self, ctx):
        super().__init__()
        self.add_item(BuildSelect(ctx))


@bot.command(name="fixa")
async def build_select(ctx):
    view = BuildSelectView(ctx)
    msg = await ctx.send("Escolha a build:", view=view)
    await ctx.message.delete(delay=5)  # Deleting the command message after 5 seconds


async def send_template(ctx, build_text):
    global template_message
    global user_roles
    global selected_weapons

    embed = discord.Embed(title="FIXA PVP", color=discord.Color.purple())
    embed.add_field(name="SAÍDA", value="MARTLOCK", inline=False)
    embed.add_field(name="BUILDS", value=build_text, inline=False)

    embed.add_field(name="👑 MAIN TANK", value=ctx.author.mention, inline=True)
    embed.add_field(name="🛡️ OFF TANK", value=" ", inline=True)
    embed.add_field(name="🍀 TANK HEALER", value=" ", inline=True)
    embed.add_field(name="🌸 PT HEALER", value=" ", inline=True)
    embed.add_field(name="🔮 SUPORTE", value=" ", inline=True)
    embed.add_field(name="⚔️ DPS 1", value=" ", inline=True)
    embed.add_field(name="⚔️ DPS 2", value=" ", inline=True)
    embed.add_field(name="⚔️ DPS 3", value=" ", inline=True)
    embed.add_field(name="⚔️ DPS 4", value=" ", inline=True)
    embed.add_field(name="⚔️ DPS 5", value=" ", inline=True)
    embed.add_field(name="📜 FILA", value=" ", inline=False)

    user_roles["MAIN TANK"] = ctx.author.mention
    selected_weapons.clear()

    await ctx.send("@everyone")
    template_message = await ctx.send(embed=embed)
    for emoji in emoji_role_mapping.keys():
        await template_message.add_reaction(emoji)


class WeaponSelect(Select):
    def __init__(self, user, options, role_prefix, ctx, template_message):
        available_options = [
            opt for opt in options if opt.label not in selected_weapons
        ]
        super().__init__(
            placeholder="Escolha sua arma",
            min_values=1,
            max_values=1,
            options=available_options,
        )
        self.user = user
        self.role_prefix = role_prefix
        self.ctx = ctx
        self.template_message = template_message

    async def callback(self, interaction: discord.Interaction):
        global user_roles
        global selected_weapons

        weapon_choice = self.values[0]
        selected_weapons.add(weapon_choice)
        if self.role_prefix == "SUPORTE":
            user_roles["SUPORTE"] = f"{weapon_choice} {self.user.mention}"
        else:
            for role in ["DPS 1", "DPS 2", "DPS 3", "DPS 4", "DPS 5"]:
                if user_roles[role] is None:
                    user_roles[role] = f"{weapon_choice} {self.user.mention}"
                    break

        await update_template_message(interaction.channel)

        await interaction.response.defer(ephemeral=True)
        await interaction.delete_original_response()


class WeaponSelectView(View):
    def __init__(self, user, role_prefix, ctx, template_message):
        options = weapon_options.get(role_prefix, [])
        super().__init__()
        if options:
            self.add_item(
                WeaponSelect(user, options, role_prefix, ctx, template_message)
            )


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    global template_message
    global user_roles
    global user_queue

    if reaction.message.id != template_message.id:
        return

    role = emoji_role_mapping.get(reaction.emoji)
    if role:
        # Check if the user is already mentioned in any role
        if (
            any(user.mention in (value or "") for value in user_roles.values())
            and role != "REMOVE"
        ):
            await reaction.message.channel.send(
                f"{user.mention}, você já está atribuído a uma função. Por favor, remova-se da função atual antes de escolher outra.",
                delete_after=10,
            )
            return

        if role == "REMOVE":
            for key, value in user_roles.items():
                if value and user.mention in value:
                    user_roles[key] = None
                    break
            # Remove user from queue
            for queue in user_queue.values():
                if user.mention in queue:
                    queue.remove(user.mention)
            await update_template_message(reaction.message.channel)
        else:
            # Check if the role is already occupied and if the role allows only one user
            if role in ["MAIN TANK", "OFF TANK", "TANK HEALER", "PT HEALER"]:
                if user_roles[role] is not None:
                    # Add user to the queue
                    if user.mention not in user_queue[role]:
                        user_queue[role].append(user.mention)
                    await reaction.message.channel.send(
                        f"{user.mention}, todas as vagas de {role} estão preenchidas. Você foi adicionado à fila.",
                        delete_after=10,
                    )
                    await update_template_message(reaction.message.channel)
                    return
                else:
                    user_roles[role] = user.mention
                    await update_template_message(reaction.message.channel)
            elif role in ["SUPORTE", "DPS"]:
                if role == "SUPORTE" and user_roles["SUPORTE"] is not None:
                    # Add user to the queue
                    if user.mention not in user_queue["SUPORTE"]:
                        user_queue["SUPORTE"].append(user.mention)
                    await reaction.message.channel.send(
                        f"{user.mention}, todas as vagas de {role} estão preenchidas. Você foi adicionado à fila.",
                        delete_after=10,
                    )
                    await update_template_message(reaction.message.channel)
                    return
                else:
                    view = WeaponSelectView(
                        user, role, reaction.message.channel, template_message
                    )
                    await reaction.message.channel.send(
                        f"{user.mention}, escolha sua arma:", view=view
                    )


async def update_template_message(channel):
    global template_message
    global user_roles
    global user_queue

    # Create new embed with updated values
    new_embed = discord.Embed(title="FIXA PVP", color=discord.Color.purple())
    new_embed.add_field(name="SAÍDA", value="MARTLOCK", inline=False)
    new_embed.add_field(
        name="BUILDS",
        value=template_message.embeds[0].fields[1].value,  # preserve the build text
        inline=False,
    )

    new_embed.add_field(
        name="👑 MAIN TANK", value=user_roles["MAIN TANK"] or " ", inline=True
    )
    new_embed.add_field(
        name="🛡️ OFF TANK", value=user_roles["OFF TANK"] or " ", inline=True
    )
    new_embed.add_field(
        name="🍀 TANK HEALER", value=user_roles["TANK HEALER"] or " ", inline=True
    )
    new_embed.add_field(
        name="🌸 PT HEALER", value=user_roles["PT HEALER"] or " ", inline=True
    )
    new_embed.add_field(
        name="🔮 SUPORTE", value=user_roles["SUPORTE"] or " ", inline=True
    )
    new_embed.add_field(name="⚔️ DPS 1", value=user_roles["DPS 1"] or " ", inline=True)
    new_embed.add_field(name="⚔️ DPS 2", value=user_roles["DPS 2"] or " ", inline=True)
    new_embed.add_field(name="⚔️ DPS 3", value=user_roles["DPS 3"] or " ", inline=True)
    new_embed.add_field(name="⚔️ DPS 4", value=user_roles["DPS 4"] or " ", inline=True)
    new_embed.add_field(name="⚔️ DPS 5", value=user_roles["DPS 5"] or " ", inline=True)

    # Update queue display
    queue_text = "\n".join(
        f"{role}: {', '.join(users) or ' '}"
        for role, users in user_queue.items()
        if users
    )
    new_embed.add_field(name="📜 FILA", value=queue_text, inline=False)

    # Send new message
    await template_message.delete()
    template_message = await channel.send(embed=new_embed)
    for emoji in emoji_role_mapping.keys():
        await template_message.add_reaction(emoji)


bot.run("MTI2NTcyODAxNzIzMDIwNDkzOA.G0Lwyb.hLy4WFSNqALSoVph4EDLvK37uMQfPuM9uaj7yE")
