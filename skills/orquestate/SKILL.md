---
name: orquestate
description: Orquestar cuentas MetaTrader 5 del workspace actual usando MQL5\Scripts\interface.py, archivos accounts/account_id/info.md, accounts/account_id/bots.ini y notificaciones Telegram. Use when Codex is asked to orchestrate accounts, coordinate account-specific bots, prepare or inspect bots.ini for an MT5 account, or notify the configured Telegram chat/channel about account orchestration status.
---

# Orquestate

## Flujo

Orquesta siempre desde la cuenta MT5 actualmente conectada. Trata cualquier orden o cambio de trading como una operacion live: no abras, cierres ni edites operaciones salvo que el usuario lo pida explicitamente.

1. Consultar la cuenta actual con la skill `interface`:

```powershell
cd C:\Users\<user-id>\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\Scripts
python interface.py --cmd=account --json
```

2. Extraer el id/login de la cuenta del JSON. Si el JSON no incluye una clave obvia, usar el login que muestre la salida de `--cmd=account`.

3. Leer `accounts/<account_id>/info.md` desde la raiz del terminal. Si no existe, pedir al usuario los datos minimos antes de crear o modificar configuracion: proposito de la cuenta, riesgo permitido, restricciones, mercados, sesiones y cualquier regla operativa.

4. Comprobar `accounts/<account_id>/bots.ini`.

5. Si `bots.ini` no existe, preguntar que bots quiere tener funcionando y que parametros necesita cada uno. No inventes bots, simbolos, timeframes, lotajes ni parametros de riesgo. Crear el archivo solo cuando el usuario haya dado la configuracion suficiente.

6. Si `bots.ini` ya existe, asumir que hay una configuracion de bots definida. No reescribirla salvo peticion expresa. Revisar su contenido y enviar un resumen por Telegram.

7. Enviar la notificacion con `scripts/send_telegram.py`. La configuracion privada vive en `accounts/<account_id>/telegram.env`.

## Archivos De Cuenta

Usar esta estructura por cuenta:

```text
accounts/
  <account_id>/
    info.md
    bots.ini
    telegram.env
```

`info.md` contiene informacion humana de la cuenta: riesgo, objetivo, limites, mercados, broker, restricciones y notas operativas.

`bots.ini` contiene la configuracion que se usara para iniciar MT5 con los bots de esa cuenta. Si no hay formato previo en el workspace, crear un INI legible y estable:

```ini
[account]
id=123456
risk_profile=segun accounts/123456/info.md

[bot:mean-reversion-eurusd]
enabled=true
expert=MQL5\Experts\mean-reversion.ex5
symbol=EURUSD
timeframe=M15
risk=0.50
set_file=MQL5\Profiles\Tester\mean-reversion-eurusd.set
notes=Configuracion confirmada por el usuario
```

`telegram.env` debe estar ignorado por Git y contener:

```dotenv
TELEGRAM_API_KEY=123456:token
TELEGRAM_CHAT=-1001234567890
TELEGRAM_CHANNEL=@canal_opcional
```

`TELEGRAM_API_KEY` y `TELEGRAM_CHAT` son obligatorios para notificar. `TELEGRAM_CHANNEL` es opcional; si falta o esta vacio, ignorarlo. No imprimir tokens completos en respuestas.

## Telegram

Enviar mensajes con el script incluido en esta skill:

```powershell
python C:\Users\<user-id>\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\skills\orquestate\scripts\send_telegram.py --account-id 123456 --message "Orquestacion revisada para la cuenta 123456"
```

El script usa una peticion HTTP GET a `https://api.telegram.org/bot<TOKEN>/sendMessage`, igual que los EAs Telegram del workspace. Envia siempre a `TELEGRAM_CHAT` y, si `TELEGRAM_CHANNEL` existe, tambien a ese destino.

Para mensajes largos o con saltos de linea, usar `--message-file`:

```powershell
python C:\Users\<user-id>\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\skills\orquestate\scripts\send_telegram.py --account-id 123456 --message-file .\accounts\123456\last-orchestration-message.txt
```

Usar `--dry-run` para validar el env y los destinos sin enviar:

```powershell
python C:\Users\<user-id>\AppData\Roaming\MetaQuotes\Terminal\<terminal-id>\MQL5\skills\orquestate\scripts\send_telegram.py --account-id 123456 --message "Prueba" --dry-run
```

## Reglas

- Preguntar al usuario que bots quiere tener funcionando si falta `accounts/<account_id>/bots.ini`.
- No crear `bots.ini` con conjeturas sobre bots, simbolos, timeframes, lotaje, riesgo o parametros.
- No modificar `bots.ini` existente salvo que el usuario lo pida o confirme cambios concretos.
- Leer `info.md` antes de proponer configuracion para respetar el riesgo y las reglas de la cuenta.
- Verificar que `.gitignore` contiene `accounts/*/telegram.env` antes de pedir o crear credenciales.
- No enviar credenciales por Telegram ni mostrarlas en la respuesta.
- Si Telegram falla, reportar codigo HTTP y respuesta resumida sin revelar el token.
