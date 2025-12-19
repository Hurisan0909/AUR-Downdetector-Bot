import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from datetime import datetime

# Botのトークンを設定
TOKEN = 'YOUR - DISCORD - TOKEN'

# AUR監視URL
AUR_URL = 'https://aur.archlinux.org'

# 通知先チャンネルID
MONITOR_CHANNEL_ID = 12345678910 #チャンネルIDをコピーすること。

# Intentsの設定
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!aur:', intents=intents)

# 監視結果を保存
last_status = None
last_message = None  # 最後に送信したメッセージを保存

@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました')
    print(f'Bot ID: {bot.user.id}')
    print('------')
    # 自動監視を開始
    check_aur_status.start()

async def ping_aur():
    """AURサーバーにpingを送信してステータスを確認"""
    try:
        async with aiohttp.ClientSession() as session:
            start_time = asyncio.get_event_loop().time()
            async with session.get(AUR_URL, timeout=10) as response:
                end_time = asyncio.get_event_loop().time()
                response_time = round((end_time - start_time) * 1000, 2)
                
                return {
                    'status': 'online' if response.status == 200 else 'error',
                    'status_code': response.status,
                    'response_time': response_time,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
    except asyncio.TimeoutError:
        return {
            'status': 'timeout',
            'status_code': None,
            'response_time': None,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {
            'status': 'error',
            'status_code': None,
            'response_time': None,
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def create_embed(result):
    """結果をembedで整形"""
    if result['status'] == 'online':
        embed = discord.Embed(
            title="✅ AUR サーバー状態",
            description="AURサーバーは正常に稼働しています",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="ステータスコード", value=f"`{result['status_code']}`", inline=True)
        embed.add_field(name="応答時間", value=f"`{result['response_time']}ms`", inline=True)
    elif result['status'] == 'timeout':
        embed = discord.Embed(
            title="⚠️ AUR サーバー状態",
            description="サーバーからの応答がタイムアウトしました",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
    else:
        embed = discord.Embed(
            title="❌ AUR サーバー状態",
            description="サーバーでエラーが発生しています",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        if result.get('status_code'):
            embed.add_field(name="ステータスコード", value=f"`{result['status_code']}`", inline=True)
        if result.get('error'):
            embed.add_field(name="エラー", value=f"`{result['error']}`", inline=False)
    
    embed.add_field(name="URL", value=AUR_URL, inline=False)
    embed.set_footer(text="AUR Downdetector Bot")
    return embed

@bot.command(name='ping')
async def ping_command(ctx):
    """AURサーバーの状態を手動でチェック"""
    global last_message
    
    # ユーザーのコマンドメッセージを削除
    try:
        await ctx.message.delete()
    except:
        pass
    
    # 前のメッセージを削除
    if last_message:
        try:
            await last_message.delete()
        except:
            pass
    
    msg = await ctx.send("AURサーバーを確認中...")
    result = await ping_aur()
    embed = create_embed(result)
    
    # 確認中メッセージを削除して結果を送信
    await msg.delete()
    last_message = await ctx.send(embed=embed)

@bot.command(name='status')
async def status_command(ctx):
    """現在の監視状態を表示"""
    global last_status, last_message
    
    # ユーザーのコマンドメッセージを削除
    try:
        await ctx.message.delete()
    except:
        pass
    
    # 前のメッセージを削除
    if last_message:
        try:
            await last_message.delete()
        except:
            pass
    
    if last_status:
        embed = create_embed(last_status)
        last_message = await ctx.send(embed=embed)
    else:
        last_message = await ctx.send("まだ監視データがありません。`!aur:ping` コマンドで確認してください。")

@tasks.loop(minutes=10)
async def check_aur_status():
    """10分ごとにAURの状態を自動チェック"""
    global last_status, last_message
    result = await ping_aur()
    
    # 指定されたチャンネルを取得
    channel = bot.get_channel(MONITOR_CHANNEL_ID)
    if not channel:
        print(f"チャンネルID {MONITOR_CHANNEL_ID} が見つかりません")
        last_status = result
        return
    
    # 前のメッセージを削除
    if last_message:
        try:
            await last_message.delete()
        except:
            pass
    
    # 常に最新の状態を表示（ステータスが変化していなくても）
    embed = create_embed(result)
    try:
        last_message = await channel.send(embed=embed)
    except Exception as e:
        print(f"メッセージ送信エラー: {e}")
    
    last_status = result

@check_aur_status.before_loop
async def before_check():
    """Botが準備できるまで待機"""
    await bot.wait_until_ready()

# Botを起動
if __name__ == '__main__':
    bot.run(TOKEN)