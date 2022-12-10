import discord
import functools

__all__ = ("build_embed", "message", "success", "warning", "failure")


def build_embed(**kwargs):
    """Build a :class:`discord.Embed` from keyword arguments.

    Parameters
    ----------
    title: Optional[str]
        The embed title.
    description: Optional[str]
        The embed description.
    url: Optional[str]
        The embed url.
    colour: Optional[Union[discord.Colour, int]]
        The embed colour. Set to ``None`` to create an embed without a colour.
        Defaults to :meth:`senko.Colour.default`.
    timestamp: datetime.datetime
        The embed timestamp.
    thumbnail: str
        The embed thumbnail.
    image: str
        The embed image.
    author: Union[str, dict]
        The embed author. When set to a string, this is used as the author name.
        When set to a dict, this is passed into :meth:`discord.Embed.set_author`.
    footer: Union[str, dict]
        The embed footer. When set to a string, this is used as the footer text.
        When set to a dict, this is passed into :meth:`discord.Embed.set_footer`.
    fields: List[dict]
        An iterable of dictionaries to pass into :meth:`discord.Embed.add_field`.

    Returns
    -------
    discord.Embed
        An embed constructed from the provided parameters.
    """
    embed = discord.Embed()
    embed.title = kwargs.get("title", None)
    embed.description = kwargs.get("description", None)
    embed.timestamp = kwargs.get("timestamp", None)
    embed.url = kwargs.get("url", None)
    embed.set_image(url=kwargs.get("image", None))
    embed.set_thumbnail(url=kwargs.get("thumbnail", None))

    colour = kwargs.get("colour", None)
    if colour is not None:
        embed.colour = colour

    author = kwargs.get("author", None)
    if isinstance(author, dict):
        embed.set_author(
            name=author["name"],
            url=author.get("url", None),
            icon_url=author.get("icon_url", None),
        )
    elif isinstance(author, str):
        embed.set_author(name=author)

    footer = kwargs.pop("footer", None)
    if isinstance(footer, dict):
        embed.set_footer(
            text=footer.get("text", None), icon_url=footer.get("icon_url", None)
        )
    elif isinstance(author, str):
        embed.set_footer(text=footer)

    for field in kwargs.pop("fields", []):
        embed.add_field(
            name=field["name"], value=field["value"], inline=field.get("inline", True)
        )

    return embed


def message(description: str = None, **kwargs) -> discord.Embed:
    """Generate a :class:`discord.Embed` with the given `description`.

    The colour of the generated embed will be set to ``0xE26682``.

    Returns
    -------
    discord.Embed
        The generated embed.
    """
    return build_embed(description=description, colour=0xE26682, **kwargs)


def success(description: str = None, **kwargs) -> discord.Embed:
    """Generate a :class:`discord.Embed` with the given `description`.

    The colour of the generated embed will be set to :func:`discord.Colour.green`.

    Returns
    -------
    discord.Embed
        The generated embed.
    """
    return build_embed(description=description, colour=discord.Colour.green(), **kwargs)


def warning(description: str = None, **kwargs) -> discord.Embed:
    """Generate a :class:`discord.Embed` with the given `description`.

    The colour of the generated embed will be set to :func:`discord.Colour.yellow`.

    Returns
    -------
    discord.Embed
        The generated embed.
    """
    return build_embed(
        description=description, colour=discord.Colour.yellow(), **kwargs
    )


def failure(description: str = None, **kwargs) -> discord.Embed:
    """Generate a :class:`discord.Embed` with the given `description`.

    The colour of the generated embed will be set to :func:`discord.Colour.red`.

    Returns
    -------
    discord.Embed
        The generated embed.
    """
    return build_embed(description=description, colour=discord.Colour.red(), **kwargs)


class Confirm(discord.ui.View):
    """A simple confirmation view with a confirm and cancel button.

    Adds a confirm and cancel button.
    Pressing either button will defer the interaction.

    Parameters
    ----------
    owner: discord.User
        The owner of this interaction.
    confirm: str
        Optional label for the confirm button. Defaults to ``Confirm``.
    cancel: str
        Optional label for the cancel button. Defaults to ``Cancel``.
    """

    def __init__(self, owner: discord.User, confirm: str = None, cancel: str = None):
        super().__init__(timeout=60)
        self.value = None
        self.owner = owner

        if confirm:
            self.confirm.label = confirm

        if cancel:
            self.cancel.label = cancel

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.owner

    def stop(self):
        super().stop()
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def process(self, interaction, value):
        self.value = value
        self.stop()
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process(interaction, False)


class Choice(discord.ui.View):
    def __init__(self, owner: discord.User, options:dict=None, allow_cancel=True):
        super().__init__(timeout=60)
        self.owner = owner
        self._options = options
        self.value = None
        self.cancelled = False

        # Add options.
        for label, value in options.items():
            button = discord.ui.Button(label=label, style=discord.ButtonStyle.green)
            button.callback = functools.partial(self.process, value=value)
            self.add_item(button)

        # Add cancel button.
        if allow_cancel:
            button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.grey)
            button.callback = functools.partial(self.process, cancelled=True)
            self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.owner

    def stop(self):
        super().stop()
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def process(self, interaction: discord.Interaction, value=None, cancelled=False):
        # Process pressed buttons and set the return value.
        self.value = value
        self.cancelled = cancelled
        self.stop()
        await interaction.response.edit_message(view=self)
