import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

TOKEN = "MTM0MDExNzUxNDA5MjU0ODE1OQ.GkekiS.2VfL6cqg8GVBXk3io9uMaHGf5sQ7scdKu1aypI"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

conn = sqlite3.connect("shop.db")
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS balances (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS channels (guild_id INTEGER PRIMARY KEY, buy_channel INTEGER, redeem_channel INTEGER)")
conn.commit()

STATIC_ROLES = {
    "VIP": 90,
    "บ้านรวย": 130
}

def add_balance(user_id, amount):
    c.execute("INSERT OR IGNORE INTO balances (user_id, balance) VALUES (?, 0)", (user_id,))
    c.execute("UPDATE balances SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def get_balance(user_id):
    c.execute("SELECT balance FROM balances WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    return row[0] if row else 0

def deduct_balance(user_id, amount):
    if get_balance(user_id) >= amount:
        c.execute("UPDATE balances SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        return True
    return False

class BuyRoleButton(discord.ui.Button):
    def __init__(self, role_name, price):
        super().__init__(label=f"{role_name} - {price}฿", style=discord.ButtonStyle.secondary)
        self.role_name = role_name
        self.price = price

    async def callback(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name=self.role_name)
        if not role:
            await interaction.response.send_message(f"ไม่พบยศ `{self.role_name}` ในเซิร์ฟเวอร์", ephemeral=True)
            return
        if interaction.user.get_role(role.id):
            await interaction.response.send_message("คุณมียศนี้อยู่แล้ว", ephemeral=True)
            return
        if deduct_balance(interaction.user.id, self.price):
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"ซื้อยศ `{role.name}` สำเร็จ!", ephemeral=True)
            c.execute("SELECT buy_channel FROM channels WHERE guild_id = ?", (interaction.guild.id,))
            row = c.fetchone()
            if row and row[0]:
                channel = bot.get_channel(row[0])
                if channel:
                    await channel.send(f"{interaction.user.mention} ได้ซื้อยศ `{role.name}` แล้ว")
        else:
            await interaction.response.send_message("ยอดเงินไม่เพียงพอ", ephemeral=True)

class RedeemModal(discord.ui.Modal, title="เติมเงินผ่านลิงก์ซอง"):
    link = discord.ui.TextInput(label="วางลิงก์ที่มีคำว่า gift", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        if "gift" in self.link.value:
            add_balance(interaction.user.id, 10)
            await interaction.response.send_message("เติมเงินผ่านลิงก์ซองทรูมันนี่สำเร็จ +10 บาท", ephemeral=True)
            c.execute("SELECT redeem_channel FROM channels WHERE guild_id = ?", (interaction.guild.id,))
            row = c.fetchone()
            if row and row[0]:
                channel = bot.get_channel(row[0])
                if channel:
                    await channel.send(f"{interaction.user.mention} เติมเงินผ่านลิงก์ซอง:\n{self.link.value}")
        else:
            await interaction.response.send_message("ลิงก์ไม่ถูกต้อง", ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label="เติมเงิน (ลิงก์ซอง)", style=discord.ButtonStyle.green)
    async def redeem_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("คุณไม่ได้เป็นคนเปิดเมนูนี้", ephemeral=True)
            return
        await interaction.response.send_modal(RedeemModal())

    @discord.ui.button(label="เช็คยอดเงิน", style=discord.ButtonStyle.blurple)
    async def check_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        balance = get_balance(interaction.user.id)
        await interaction.response.send_message(f"ยอดเงินของคุณคือ {balance} บาท", ephemeral=True)

    @discord.ui.button(label="ซื้อยศ", style=discord.ButtonStyle.gray)
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View(timeout=60)
        for name, price in STATIC_ROLES.items():
            view.add_item(BuyRoleButton(name, price))
        await interaction.response.send_message("เลือกยศที่ต้องการซื้อ:", view=view, ephemeral=True)

@tree.command(name="ตั้งร้าน")
async def setup_shop(interaction: discord.Interaction):
    embed = discord.Embed(
        title="ชีวิตในรั้วของชาติ",
        description="บริการขายยศในแมพชีวิตในรั้วของชาติ",
        color=discord.Color.green()
    )
    embed.set_image(url="https://img5.pic.in.th/file/secure-sv1/10000193352c78604bf52841d2.gif")
    await interaction.response.send_message(embed=embed, view=ShopView(interaction.user))

@tree.command(name="เสกเงิน")
@app_commands.describe(member="ผู้ใช้", amount="จำนวนเงิน")
async def give_money(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return
    add_balance(member.id, amount)
    await interaction.response.send_message(f"เสกเงิน {amount} บาทให้ {member.mention} แล้ว", ephemeral=True)

@tree.command(name="ลดเงิน")
@app_commands.describe(member="ผู้ใช้", amount="จำนวนเงิน")
async def take_money(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return
    if get_balance(member.id) < amount:
        await interaction.response.send_message("ผู้ใช้มียอดเงินไม่พอจะหัก", ephemeral=True)
        return
    deduct_balance(member.id, amount)
    await interaction.response.send_message(f"ลดเงิน {amount} บาทจาก {member.mention} แล้ว", ephemeral=True)

@tree.command(name="ห้องแสดงรายการซื้อ")
@app_commands.describe(channel="เลือกห้อง")
async def set_buy_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("คุณไม่มีสิทธิ์ตั้งค่า", ephemeral=True)
        return
    c.execute("INSERT OR IGNORE INTO channels (guild_id, buy_channel, redeem_channel) VALUES (?, NULL, NULL)", (interaction.guild.id,))
    c.execute("UPDATE channels SET buy_channel = ? WHERE guild_id = ?", (channel.id, interaction.guild.id))
    conn.commit()
    await interaction.response.send_message(f"ตั้งห้องแจ้งรายการซื้อเป็น {channel.mention}", ephemeral=True)

@tree.command(name="ห้องแสดงลิงก์ซอง")
@app_commands.describe(channel="เลือกห้อง")
async def set_redeem_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("คุณไม่มีสิทธิ์ตั้งค่า", ephemeral=True)
        return
    c.execute("INSERT OR IGNORE INTO channels (guild_id, buy_channel, redeem_channel) VALUES (?, NULL, NULL)", (interaction.guild.id,))
    c.execute("UPDATE channels SET redeem_channel = ? WHERE guild_id = ?", (channel.id, interaction.guild.id))
    conn.commit()
    await interaction.response.send_message(f"ตั้งห้องแจ้งลิงก์ซองเป็น {channel.mention}", ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    print(f"บอทออนไลน์ในชื่อ {bot.user}")

bot.run(TOKEN)
