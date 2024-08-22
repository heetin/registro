import discord
from discord.ext import commands
import requests
import datetime  # Agregado para manejar fechas y horas

TOKEN = 'MTI3NTM2NzcyMTU1MDIxNzIzOA.GlDi5F.eP6N4nfXcr0u6MkftVQfh69Rc_FK3G0IoXQkcI'  # Reemplaza con el token de tu bot
WEBHOOK_URL = 'https://n8n1.elegisprepaga.com.ar/webhook/087060ba-d52e-49c4-b78b-83c80a0c0c58'
CANAL_ESPECIFICO_ID = 1275000253421977630  # ID del canal que quieres leer

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents, case_insensitive=True)

# Diccionario para almacenar la información de registro y el tiempo de la última acción
registro_usuarios = {}

def formatear_numero(numero):
    """Función para formatear un número grande con puntos."""
    return f"{numero:,}".replace(",", ".")

def buscar_jugador(nick):
    search_url = f"https://gameinfo.albiononline.com/api/gameinfo/search?q={nick}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        search_results = response.json()
    except requests.RequestException as e:
        return None, f"Error al buscar el jugador: {e}"

    if not search_results.get('players'):
        return None, f"No se encontró ningún jugador con el nick '{nick}'."

    player = search_results['players'][0]
    player_id = player.get('Id')

    player_details_url = f"https://gameinfo.albiononline.com/api/gameinfo/players/{player_id}"
    try:
        details_response = requests.get(player_details_url, headers=headers)
        details_response.raise_for_status()
        player_details = details_response.json()
    except requests.RequestException as e:
        return None, f"Error al obtener detalles del jugador: {e}"

    # Extraer la información solicitada
    fame_pve = formatear_numero(player_details.get('LifetimeStatistics', {}).get('PvE', {}).get('Total', 0))
    fame_pvp = formatear_numero(player_details.get('KillFame', 0))
    pvp_ratio = player_details.get('FameRatio', 'Desconocido')
    crafting_fame = formatear_numero(player_details.get('LifetimeStatistics', {}).get('Crafting', {}).get('Total', 0))
    fishing_fame = formatear_numero(player_details.get('LifetimeStatistics', {}).get('FishingFame', 0))
    last_connection = player_details.get('LifetimeStatistics', {}).get('Timestamp', 'Desconocido')
    hellgate_fame = formatear_numero(player_details.get('LifetimeStatistics', {}).get('PvE', {}).get('Hellgate', 0))
    corrupted_fame = formatear_numero(player_details.get('LifetimeStatistics', {}).get('PvE', {}).get('CorruptedDungeon', 0))
    mist_fame = formatear_numero(player_details.get('LifetimeStatistics', {}).get('PvE', {}).get('Mists', 0))

    # Formatear la información
    info_jugador = (
        f"\n=== Información del Jugador ===\n"
        f"Nombre: {player_details.get('Name')}\n"
        f"Gremio: {player_details.get('GuildName', 'N/A')}\n"
        f"Alianza: {player_details.get('AllianceName', 'N/A')}\n"
        f"Fama PvE: {fame_pve}\n"
        f"Fama PvP: {fame_pvp}\n"
        f"Ratio PvP: {pvp_ratio}\n"
        f"Fama Crafting: {crafting_fame}\n"
        f"Fama Pesca: {fishing_fame}\n"
        f"Fama Hellgates: {hellgate_fame}\n"
        f"Fama Corruptas: {corrupted_fame}\n"
        f"Fama Mists: {mist_fame}\n"
        f"Última Conexión (Timestamp): {last_connection}\n"
        f"==========[MESA ELITE]============\n"
    )

    # Verifica si el gremio está vacío o no está en la lista especificada
    gremios_validos = ["4K TEAM ELITE", "Ursinos", "4K TEAM ELITE II", "Latinos-infiltrados", "Focaris"]
    gremio = player_details.get('GuildName', '').strip()
    if gremio.upper() not in [gremio.upper() for gremio in gremios_validos] or not gremio:
        gremio = 'TOPO'
    
    return gremio, info_jugador, player_details

def enviar_datos_webhook(player_details, usuario_discord, fecha_registro):
    params = {
        'nombre': player_details.get('Name'),
        'gremio': player_details.get('GuildName', ''),
        'alianza': player_details.get('AllianceName', ''),
        'kills': player_details.get('LifetimeStatistics', {}).get('PvP', {}).get('Kills', 0),
        'fama_pvp': player_details.get('KillFame', 0),
        'fama_pve': player_details.get('LifetimeStatistics', {}).get('PvE', {}).get('Total', 0),
        'ultima_actividad': player_details.get('LifetimeStatistics', {}).get('Timestamp', 'Desconocido'),
        'usuario_discord': usuario_discord,  # Añadir el usuario de Discord
        'fecha_registro': fecha_registro,  # Añadir la fecha y hora del registro
        'fama_crafting': player_details.get('LifetimeStatistics', {}).get('Crafting', {}).get('Total', 0),
        'fama_pesca': player_details.get('LifetimeStatistics', {}).get('FishingFame', 0),
        'fama_hellgate': player_details.get('LifetimeStatistics', {}).get('PvE', {}).get('Hellgate', 0),
        'fama_corruptas': player_details.get('LifetimeStatistics', {}).get('PvE', {}).get('CorruptedDungeon', 0),
        'fama_mists': player_details.get('LifetimeStatistics', {}).get('PvE', {}).get('Mists', 0),
    }
    
    try:
        response = requests.get(WEBHOOK_URL, params=params)
        response.raise_for_status()
        print("Datos enviados correctamente al webhook")
    except requests.RequestException as e:
        print(f"Error al enviar datos al webhook: {e}")

@bot.command(name='registro')
async def registro(ctx, *, nick):
    if ctx.channel.id != CANAL_ESPECIFICO_ID:
        return  # No hacer nada si el mensaje no proviene del canal específico

    user_id = ctx.author.id
    now = datetime.datetime.now()

    # Verificar el tiempo de la última acción
    if user_id in registro_usuarios:
        last_registration_time = registro_usuarios[user_id]
        time_diff = now - last_registration_time
        if time_diff.total_seconds() < 1200:  # 1200 segundos = 20 minutos
            remaining_time = 1200 - time_diff.total_seconds()
            await ctx.send(f"Debes esperar {int(remaining_time // 60)} minutos antes de registrarte nuevamente.")
            return

    # Envía mensaje inicial de espera
    mensaje_espera = await ctx.send("Aguarda un instante estoy procesando la información de registro. Luego esperá que te demos el acceso y rol")

    gremio, info_jugador, player_details = buscar_jugador(nick)
    if not gremio:
        await mensaje_espera.edit(content=info_jugador)
        return

    # Formatear el nuevo apodo
    nuevo_apodo = f"[{gremio}] {nick}"

    # Cambiar el apodo del usuario en Discord
    miembro = ctx.guild.get_member(ctx.author.id)
    if miembro:
        try:
            await miembro.edit(nick=nuevo_apodo)
            await mensaje_espera.edit(content=f"Apodo cambiado a: {nuevo_apodo}\n{info_jugador}")  # Actualiza el mensaje con la información del jugador
            # Actualizar el tiempo de la última acción
            registro_usuarios[user_id] = now
            
            # Enviar los datos del jugador al webhook con fecha y hora de registro
            fecha_registro = now.strftime("%Y-%m-%d %H:%M:%S")
            enviar_datos_webhook(player_details, ctx.author.name, fecha_registro)
            
        except discord.Forbidden:
            await mensaje_espera.edit(content="No tengo permisos para cambiar el apodo. Verifica los permisos del bot.")
        except discord.HTTPException as e:
            await mensaje_espera.edit(content=f"Error al cambiar el apodo: {e}")
    else:
        await mensaje_espera.edit(content="No se pudo encontrar al miembro en el servidor.")

bot.run(TOKEN)
