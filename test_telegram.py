# -*- coding: utf-8 -*-
"""
Test de notificación Telegram
"""
import sys
import io
import asyncio
from telegram import Bot

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

async def send_test():
    bot = Bot(token='8577007615:AAHy31IegzvbezCpyNfIlaZh_IsKuV-4M9A')
    await bot.send_message(
        chat_id='6265548967',
        text='🧪 TEST BOT FTMO\n\n✅ Conexión Telegram funcionando correctamente!\n\nEl bot está listo para enviar notificaciones de trades.'
    )
    print("✅ Mensaje de prueba enviado a Telegram")

if __name__ == '__main__':
    asyncio.run(send_test())
