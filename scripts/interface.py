#!/usr/bin/env python
"""
CLI para operar MetaTrader 5 desde Python.

Ejemplos:
  python interface.py --cmd=open --type=buy --market=EURUSD --lot=0.10 --sl-points=200 --tp-points=400
  python interface.py --cmd=open --type=buylimit --market=EURUSD --lot=0.10 --price=1.08000 --SL=1.07500 --TP=1.09000
  python interface.py --cmd=close --id=322334
  python interface.py --cmd=edit --id=23232 --TP=1.09250
  python interface.py --cmd=history --last=10
  python interface.py --cmd=opened
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Any, Iterable


SUCCESS_RETCODES = {
    "TRADE_RETCODE_DONE",
    "TRADE_RETCODE_DONE_PARTIAL",
    "TRADE_RETCODE_PLACED",
}

ORDER_TYPES = {
    "buy": "ORDER_TYPE_BUY",
    "sell": "ORDER_TYPE_SELL",
    "buylimit": "ORDER_TYPE_BUY_LIMIT",
    "buy_limit": "ORDER_TYPE_BUY_LIMIT",
    "selllimit": "ORDER_TYPE_SELL_LIMIT",
    "sell_limit": "ORDER_TYPE_SELL_LIMIT",
    "buystop": "ORDER_TYPE_BUY_STOP",
    "buy_stop": "ORDER_TYPE_BUY_STOP",
    "sellstop": "ORDER_TYPE_SELL_STOP",
    "sell_stop": "ORDER_TYPE_SELL_STOP",
    "buystoplimit": "ORDER_TYPE_BUY_STOP_LIMIT",
    "buy_stop_limit": "ORDER_TYPE_BUY_STOP_LIMIT",
    "sellstoplimit": "ORDER_TYPE_SELL_STOP_LIMIT",
    "sell_stop_limit": "ORDER_TYPE_SELL_STOP_LIMIT",
}

FILLINGS = {
    "fok": "ORDER_FILLING_FOK",
    "ioc": "ORDER_FILLING_IOC",
    "return": "ORDER_FILLING_RETURN",
    "boc": "ORDER_FILLING_BOC",
}

TIME_TYPES = {
    "gtc": "ORDER_TIME_GTC",
    "day": "ORDER_TIME_DAY",
    "specified": "ORDER_TIME_SPECIFIED",
    "specified_day": "ORDER_TIME_SPECIFIED_DAY",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interface CLI para abrir, cerrar, editar y consultar operaciones MT5.",
        add_help=True,
    )

    parser.add_argument("--cmd", default="help", help="Comando: help, open, close, edit, cancel, opened, orders, history, hystory, account, symbol.")
    parser.add_argument("--market", "--symbol", dest="market", help="Simbolo/mercado, por ejemplo EURUSD.")
    parser.add_argument("--type", dest="order_type", help="Tipo: buy, sell, buylimit, selllimit, buystop, sellstop, buystoplimit, sellstoplimit.")
    parser.add_argument("--lot", "--volume", dest="lot", type=float, help="Volumen en lotes.")
    parser.add_argument("--price", type=float, help="Precio de entrada. Obligatorio para ordenes pendientes.")
    parser.add_argument("--stoplimit", "--stop-limit", dest="stoplimit", type=float, help="Precio limite para buy_stop_limit/sell_stop_limit.")
    parser.add_argument("--id", dest="ticket", type=int, help="Ticket de posicion u orden.")
    parser.add_argument("--all", dest="close_all", action="store_true", help="Con --cmd=close cierra todas las posiciones, opcionalmente filtradas por --market.")

    parser.add_argument("--SL", "--sl", dest="sl", type=float, help="Stop loss como precio absoluto.")
    parser.add_argument("--TP", "--tp", dest="tp", type=float, help="Take profit como precio absoluto.")
    parser.add_argument("--sl-points", type=float, help="Stop loss como distancia en puntos desde el precio de entrada/posicion.")
    parser.add_argument("--tp-points", type=float, help="Take profit como distancia en puntos desde el precio de entrada/posicion.")
    parser.add_argument("--sl-pips", type=float, help="Stop loss como distancia en pips desde el precio de entrada/posicion.")
    parser.add_argument("--tp-pips", type=float, help="Take profit como distancia en pips desde el precio de entrada/posicion.")

    parser.add_argument("--deviation", type=int, default=20, help="Desviacion maxima en puntos para operaciones a mercado.")
    parser.add_argument("--magic", type=int, default=20260416, help="Magic number enviado a MT5.")
    parser.add_argument("--comment", default="interface.py", help="Comentario de la orden.")
    parser.add_argument("--filling", choices=sorted(FILLINGS), help="Modo de llenado: fok, ioc, return, boc. Si se omite se usa auto.")
    parser.add_argument("--time-type", choices=sorted(TIME_TYPES), default="gtc", help="Duracion de orden pendiente.")
    parser.add_argument("--expiration", help="Expiracion ISO para orden pendiente, por ejemplo 2026-04-16T23:59:00.")

    parser.add_argument("--last", type=int, default=10, help="Cantidad de filas para history/hystory.")
    parser.add_argument("--days", type=int, default=30, help="Dias hacia atras para history si no se usa --from.")
    parser.add_argument("--from", dest="from_date", help="Inicio de history en ISO, por ejemplo 2026-04-01 o 2026-04-01T09:00:00.")
    parser.add_argument("--to", dest="to_date", help="Fin de history en ISO. Por defecto ahora.")

    parser.add_argument("--terminal", help="Ruta opcional al terminal64.exe de MetaTrader 5.")
    parser.add_argument("--login", type=int, help="Login opcional de la cuenta MT5.")
    parser.add_argument("--password", help="Password opcional de la cuenta MT5.")
    parser.add_argument("--server", help="Servidor opcional de la cuenta MT5.")
    parser.add_argument("--portable", action="store_true", help="Inicializa MT5 en modo portable si se usa --terminal.")
    parser.add_argument("--json", action="store_true", help="Imprime respuestas en JSON cuando sea posible.")
    parser.add_argument("--dry-run", action="store_true", help="Construye y muestra la peticion sin enviarla a MT5.")

    return parser.parse_args()


def detailed_help() -> None:
    print(
        """
Uso general:
  python interface.py --cmd=<comando> [parametros]

Comandos:
  help       Muestra esta ayuda ampliada.
  open       Abre una posicion a mercado o crea una orden pendiente.
  close      Cierra una posicion por --id, o todas con --all.
  edit       Modifica SL/TP de una posicion o modifica una orden pendiente.
  cancel     Cancela una orden pendiente por --id.
  opened     Lista posiciones abiertas.
  orders     Lista ordenes pendientes.
  history    Lista las ultimas operaciones/deals del historial.
  hystory    Alias tolerante de history.
  account    Muestra informacion de la cuenta.
  symbol     Muestra informacion y tick actual de --market.

Parametros principales:
  --market / --symbol      Simbolo: EURUSD, GBPUSD, XAUUSD, etc.
  --type                  buy, sell, buylimit, selllimit, buystop, sellstop,
                          buystoplimit, sellstoplimit.
  --lot / --volume        Volumen en lotes.
  --price                 Precio de entrada. Requerido en ordenes pendientes.
  --stoplimit             Precio limite para ordenes stop-limit.
  --id                    Ticket de posicion u orden.
  --SL / --sl             Stop loss como precio absoluto.
  --TP / --tp             Take profit como precio absoluto.
  --sl-points             Stop loss como distancia en puntos.
  --tp-points             Take profit como distancia en puntos.
  --sl-pips               Stop loss como distancia en pips.
  --tp-pips               Take profit como distancia en pips.
  --deviation             Desviacion maxima en puntos para entradas/cierres a mercado.
  --magic                 Magic number.
  --comment               Comentario.
  --filling               fok, ioc, return o boc. Si falla el llenado, prueba otro.
  --time-type             gtc, day, specified, specified_day.
  --expiration            Fecha ISO si --time-type requiere expiracion.
  --last                  Numero de filas para history, por defecto 10.
  --days                  Rango hacia atras para history, por defecto 30.
  --from / --to           Rango ISO para history.
  --terminal              Ruta al terminal64.exe si Python no encuentra MT5 abierto.
  --login --password --server
                          Login opcional antes de ejecutar el comando.
  --json                  Salida JSON.
  --dry-run               Muestra la peticion que se enviaria, sin ejecutar la orden.

Ejemplos:
  python interface.py --cmd=open --type=buy --market=EURUSD --lot=0.10 --sl-points=200 --tp-points=400
  python interface.py --cmd=open --type=buylimit --market=EURUSD --lot=0.10 --price=1.08000 --SL=1.07500 --TP=1.09000
  python interface.py --cmd=edit --id=23232 --TP=1.09250
  python interface.py --cmd=edit --id=23232 --sl-points=150 --tp-points=300
  python interface.py --cmd=close --id=322334
  python interface.py --cmd=close --all --market=EURUSD
  python interface.py --cmd=cancel --id=998877
  python interface.py --cmd=opened
  python interface.py --cmd=orders --market=EURUSD
  python interface.py --cmd=history --last=10

Nota importante:
  --SL y --TP son precios absolutos, que es lo que espera MT5.
  Para distancias como "23 puntos" usa --sl-points=23 o --tp-points=23.
"""
    )


def die(message: str, code: int = 2) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_mt5() -> Any:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "ERROR: No se pudo importar MetaTrader5. Instala el paquete con: python -m pip install MetaTrader5"
        ) from exc
    return mt5


def initialize_mt5(args: argparse.Namespace) -> Any:
    mt5 = load_mt5()

    init_kwargs: dict[str, Any] = {}
    if args.terminal:
        init_kwargs["path"] = args.terminal
    if args.portable:
        init_kwargs["portable"] = True

    if not mt5.initialize(**init_kwargs):
        die(f"No se pudo inicializar MT5. last_error={mt5.last_error()}")

    if args.login is not None:
        if not args.password or not args.server:
            mt5.shutdown()
            die("--login requiere tambien --password y --server.")
        if not mt5.login(args.login, password=args.password, server=args.server):
            error = mt5.last_error()
            mt5.shutdown()
            die(f"No se pudo hacer login en MT5. last_error={error}")

    return mt5


def constant(mt5: Any, name: str) -> int:
    if not hasattr(mt5, name):
        die(f"La instalacion de MetaTrader5 no expone la constante {name}.")
    return int(getattr(mt5, name))


def normalize_type(order_type: str | None) -> str:
    if not order_type:
        die("--cmd=open requiere --type.")
    key = order_type.lower().replace("-", "_")
    if key not in ORDER_TYPES:
        die(f"Tipo de orden no soportado: {order_type}. Usa --cmd=help.")
    return key


def is_buy_type(type_key: str) -> bool:
    return type_key.startswith("buy")


def is_market_type(type_key: str) -> bool:
    return type_key in {"buy", "sell"}


def is_stop_limit_type(type_key: str) -> bool:
    return ORDER_TYPES[type_key].endswith("_STOP_LIMIT")


def ensure_symbol(mt5: Any, market: str | None) -> Any:
    if not market:
        die("Este comando requiere --market.")
    info = mt5.symbol_info(market)
    if info is None:
        die(f"Simbolo no encontrado en MT5: {market}")
    if not info.visible and not mt5.symbol_select(market, True):
        die(f"No se pudo seleccionar el simbolo {market}. last_error={mt5.last_error()}")
    return info


def tick_for_symbol(mt5: Any, market: str) -> Any:
    tick = mt5.symbol_info_tick(market)
    if tick is None:
        die(f"No hay tick disponible para {market}. last_error={mt5.last_error()}")
    return tick


def pip_size(symbol_info: Any) -> float:
    point = float(symbol_info.point)
    digits = int(symbol_info.digits)
    return point * 10 if digits in {3, 5} else point


def round_price(symbol_info: Any, value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), int(symbol_info.digits))


def distance_price(symbol_info: Any, points: float | None, pips: float | None) -> float | None:
    if points is not None and pips is not None:
        die("Usa solo una distancia: points o pips, no ambas.")
    if points is not None:
        return float(points) * float(symbol_info.point)
    if pips is not None:
        return float(pips) * pip_size(symbol_info)
    return None


def resolve_sl_tp(
    args: argparse.Namespace,
    symbol_info: Any,
    is_buy: bool,
    reference_price: float,
    current_sl: float = 0.0,
    current_tp: float = 0.0,
) -> tuple[float, float]:
    sl = args.sl if args.sl is not None else (current_sl or 0.0)
    tp = args.tp if args.tp is not None else (current_tp or 0.0)

    sl_distance = distance_price(symbol_info, args.sl_points, args.sl_pips)
    tp_distance = distance_price(symbol_info, args.tp_points, args.tp_pips)

    if args.sl is not None and sl_distance is not None:
        die("No combines --SL/--sl con --sl-points o --sl-pips.")
    if args.tp is not None and tp_distance is not None:
        die("No combines --TP/--tp con --tp-points o --tp-pips.")

    if sl_distance is not None:
        sl = reference_price - sl_distance if is_buy else reference_price + sl_distance
    if tp_distance is not None:
        tp = reference_price + tp_distance if is_buy else reference_price - tp_distance

    return round_price(symbol_info, sl) or 0.0, round_price(symbol_info, tp) or 0.0


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        die(f"Fecha invalida: {value}. Usa formato ISO como 2026-04-16 o 2026-04-16T12:30:00.")
    return None


def parse_expiration(value: str | None) -> int | None:
    parsed = parse_datetime(value)
    return int(parsed.timestamp()) if parsed else None


def request_filling(mt5: Any, args: argparse.Namespace, pending: bool) -> int:
    if args.filling:
        return constant(mt5, FILLINGS[args.filling])
    if pending:
        return constant(mt5, "ORDER_FILLING_RETURN")
    return constant(mt5, "ORDER_FILLING_IOC")


def request_time_type(mt5: Any, args: argparse.Namespace) -> int:
    return constant(mt5, TIME_TYPES[args.time_type])


def as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


def retcode_name(mt5: Any, retcode: int | None) -> str:
    if retcode is None:
        return ""
    for name in dir(mt5):
        if name.startswith("TRADE_RETCODE_") and getattr(mt5, name) == retcode:
            return name
    return str(retcode)


def print_result(mt5: Any, args: argparse.Namespace, result: Any) -> None:
    data = as_dict(result)
    data["retcode_name"] = retcode_name(mt5, data.get("retcode"))
    if args.json:
        print(json.dumps(data, default=str, indent=2, sort_keys=True))
    else:
        print(f"retcode: {data.get('retcode')} ({data.get('retcode_name')})")
        for key in ("comment", "order", "deal", "volume", "price", "bid", "ask", "request_id"):
            if key in data:
                print(f"{key}: {data.get(key)}")
        if "request" in data and data["request"]:
            print(f"request: {data['request']}")

    if data.get("retcode_name") not in SUCCESS_RETCODES:
        raise SystemExit(3)


def print_dry_run(args: argparse.Namespace, request: dict[str, Any]) -> None:
    if args.json:
        print(json.dumps({"dry_run": True, "request": request}, default=str, indent=2, sort_keys=True))
    else:
        print("DRY RUN: no se envio ninguna peticion a MT5.")
        for key, value in request.items():
            print(f"{key}: {value}")


def print_table(rows: list[dict[str, Any]], columns: list[str], json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(rows, default=str, indent=2, sort_keys=True))
        return
    if not rows:
        print("Sin resultados.")
        return

    widths = {
        col: max(len(col), *(len(str(row.get(col, ""))) for row in rows))
        for col in columns
    }
    print("  ".join(col.ljust(widths[col]) for col in columns))
    print("  ".join("-" * widths[col] for col in columns))
    for row in rows:
        print("  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns))


def open_order(mt5: Any, args: argparse.Namespace) -> None:
    type_key = normalize_type(args.order_type)
    symbol_info = ensure_symbol(mt5, args.market)
    market = args.market

    if args.lot is None or args.lot <= 0:
        die("--cmd=open requiere --lot mayor que 0.")

    pending = not is_market_type(type_key)
    tick = tick_for_symbol(mt5, market)
    is_buy = is_buy_type(type_key)
    reference_price = float(tick.ask if is_buy else tick.bid)

    if pending:
        if args.price is None:
            die("Las ordenes pendientes requieren --price.")
        reference_price = float(args.price)
    elif args.price is not None:
        reference_price = float(args.price)

    if is_stop_limit_type(type_key) and args.stoplimit is None:
        die("Las ordenes stop-limit requieren --stoplimit.")

    sl, tp = resolve_sl_tp(args, symbol_info, is_buy, reference_price)

    request: dict[str, Any] = {
        "action": constant(mt5, "TRADE_ACTION_PENDING" if pending else "TRADE_ACTION_DEAL"),
        "symbol": market,
        "volume": float(args.lot),
        "type": constant(mt5, ORDER_TYPES[type_key]),
        "price": round_price(symbol_info, reference_price),
        "sl": sl,
        "tp": tp,
        "deviation": int(args.deviation),
        "magic": int(args.magic),
        "comment": args.comment,
        "type_time": request_time_type(mt5, args),
        "type_filling": request_filling(mt5, args, pending),
    }

    if args.stoplimit is not None:
        request["stoplimit"] = round_price(symbol_info, args.stoplimit)
    expiration = parse_expiration(args.expiration)
    if expiration is not None:
        request["expiration"] = expiration

    if args.dry_run:
        print_dry_run(args, request)
        return

    result = mt5.order_send(request)
    print_result(mt5, args, result)


def get_position_by_ticket(mt5: Any, ticket: int) -> Any | None:
    positions = mt5.positions_get(ticket=ticket)
    if positions:
        return positions[0]
    return None


def get_order_by_ticket(mt5: Any, ticket: int) -> Any | None:
    orders = mt5.orders_get(ticket=ticket)
    if orders:
        return orders[0]
    return None


def close_position(mt5: Any, args: argparse.Namespace, position: Any) -> Any:
    symbol_info = ensure_symbol(mt5, position.symbol)
    tick = tick_for_symbol(mt5, position.symbol)
    is_buy_position = int(position.type) == constant(mt5, "POSITION_TYPE_BUY")
    close_type = constant(mt5, "ORDER_TYPE_SELL" if is_buy_position else "ORDER_TYPE_BUY")
    price = tick.bid if is_buy_position else tick.ask
    volume = float(args.lot) if args.lot is not None else float(position.volume)
    if volume <= 0:
        die("--lot debe ser mayor que 0 si se usa cierre parcial.")
    if volume > float(position.volume):
        die(f"No puedes cerrar {volume}; la posicion solo tiene {position.volume}.")

    request = {
        "action": constant(mt5, "TRADE_ACTION_DEAL"),
        "position": int(position.ticket),
        "symbol": position.symbol,
        "volume": volume,
        "type": close_type,
        "price": round_price(symbol_info, float(price)),
        "deviation": int(args.deviation),
        "magic": int(args.magic),
        "comment": args.comment,
        "type_time": constant(mt5, "ORDER_TIME_GTC"),
        "type_filling": request_filling(mt5, args, pending=False),
    }
    if args.dry_run:
        return request
    return mt5.order_send(request)


def close_command(mt5: Any, args: argparse.Namespace) -> None:
    if args.close_all:
        positions = mt5.positions_get(symbol=args.market) if args.market else mt5.positions_get()
        positions = list(positions or [])
        if not positions:
            print("No hay posiciones para cerrar.")
            return
        results = []
        exit_code = 0
        for position in positions:
            result = close_position(mt5, args, position)
            data = as_dict(result)
            if args.dry_run:
                data = {"dry_run": True, "position": int(position.ticket), "request": result}
            data["retcode_name"] = retcode_name(mt5, data.get("retcode"))
            data["position"] = int(position.ticket)
            results.append(data)
            if not args.dry_run and data["retcode_name"] not in SUCCESS_RETCODES:
                exit_code = 3
        if args.json:
            print(json.dumps(results, default=str, indent=2, sort_keys=True))
        else:
            print_table(
                results,
                ["position", "retcode", "retcode_name", "comment", "order", "deal"],
                json_output=False,
            )
        raise SystemExit(exit_code)

    if args.ticket is None:
        die("--cmd=close requiere --id, o usa --all.")
    position = get_position_by_ticket(mt5, args.ticket)
    if position is None:
        die(f"No hay posicion abierta con ticket {args.ticket}. Si es una orden pendiente usa --cmd=cancel.")
    result = close_position(mt5, args, position)
    if args.dry_run:
        print_dry_run(args, result)
        return
    print_result(mt5, args, result)


def edit_command(mt5: Any, args: argparse.Namespace) -> None:
    if args.ticket is None:
        die("--cmd=edit requiere --id.")

    position = get_position_by_ticket(mt5, args.ticket)
    if position is not None:
        symbol_info = ensure_symbol(mt5, position.symbol)
        is_buy = int(position.type) == constant(mt5, "POSITION_TYPE_BUY")
        reference_price = float(position.price_open)
        sl, tp = resolve_sl_tp(args, symbol_info, is_buy, reference_price, float(position.sl), float(position.tp))
        request = {
            "action": constant(mt5, "TRADE_ACTION_SLTP"),
            "position": int(position.ticket),
            "symbol": position.symbol,
            "sl": sl,
            "tp": tp,
            "magic": int(args.magic),
            "comment": args.comment,
        }
        if args.dry_run:
            print_dry_run(args, request)
            return
        result = mt5.order_send(request)
        print_result(mt5, args, result)
        return

    order = get_order_by_ticket(mt5, args.ticket)
    if order is None:
        die(f"No se encontro posicion ni orden pendiente con ticket {args.ticket}.")

    symbol_info = ensure_symbol(mt5, order.symbol)
    order_type_name = "buy" if int(order.type) in {
        constant(mt5, "ORDER_TYPE_BUY_LIMIT"),
        constant(mt5, "ORDER_TYPE_BUY_STOP"),
        constant(mt5, "ORDER_TYPE_BUY_STOP_LIMIT"),
    } else "sell"
    is_buy = order_type_name == "buy"
    reference_price = float(args.price if args.price is not None else order.price_open)
    sl, tp = resolve_sl_tp(args, symbol_info, is_buy, reference_price, float(order.sl), float(order.tp))

    request = {
        "action": constant(mt5, "TRADE_ACTION_MODIFY"),
        "order": int(order.ticket),
        "symbol": order.symbol,
        "price": round_price(symbol_info, reference_price),
        "sl": sl,
        "tp": tp,
        "type_time": request_time_type(mt5, args),
        "type_filling": request_filling(mt5, args, pending=True),
    }
    stoplimit = args.stoplimit if args.stoplimit is not None else getattr(order, "price_stoplimit", 0.0)
    if stoplimit:
        request["stoplimit"] = round_price(symbol_info, float(stoplimit))
    expiration = parse_expiration(args.expiration)
    if expiration is not None:
        request["expiration"] = expiration
    elif getattr(order, "time_expiration", 0):
        request["expiration"] = int(order.time_expiration)

    if args.dry_run:
        print_dry_run(args, request)
        return

    result = mt5.order_send(request)
    print_result(mt5, args, result)


def cancel_command(mt5: Any, args: argparse.Namespace) -> None:
    if args.ticket is None:
        die("--cmd=cancel requiere --id.")
    order = get_order_by_ticket(mt5, args.ticket)
    if order is None:
        die(f"No hay orden pendiente con ticket {args.ticket}.")
    request = {
        "action": constant(mt5, "TRADE_ACTION_REMOVE"),
        "order": int(order.ticket),
        "symbol": order.symbol,
        "magic": int(args.magic),
        "comment": args.comment,
    }
    if args.dry_run:
        print_dry_run(args, request)
        return
    result = mt5.order_send(request)
    print_result(mt5, args, result)


def order_type_lookup(mt5: Any, prefix: str) -> dict[int, str]:
    return {
        int(getattr(mt5, name)): name.replace(prefix, "")
        for name in dir(mt5)
        if name.startswith(prefix)
    }


def rows_from_positions(mt5: Any, positions: Iterable[Any]) -> list[dict[str, Any]]:
    type_names = order_type_lookup(mt5, "POSITION_TYPE_")
    rows = []
    for pos in positions:
        rows.append(
            {
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": type_names.get(int(pos.type), pos.type),
                "volume": pos.volume,
                "open": pos.price_open,
                "sl": pos.sl,
                "tp": pos.tp,
                "price": pos.price_current,
                "profit": pos.profit,
                "magic": pos.magic,
                "comment": pos.comment,
            }
        )
    return rows


def opened_command(mt5: Any, args: argparse.Namespace) -> None:
    positions = mt5.positions_get(symbol=args.market) if args.market else mt5.positions_get()
    rows = rows_from_positions(mt5, list(positions or []))
    print_table(rows, ["ticket", "symbol", "type", "volume", "open", "sl", "tp", "price", "profit", "magic", "comment"], args.json)


def rows_from_orders(mt5: Any, orders: Iterable[Any]) -> list[dict[str, Any]]:
    type_names = order_type_lookup(mt5, "ORDER_TYPE_")
    rows = []
    for order in orders:
        rows.append(
            {
                "ticket": order.ticket,
                "symbol": order.symbol,
                "type": type_names.get(int(order.type), order.type),
                "volume": order.volume_initial,
                "price": order.price_open,
                "stoplimit": getattr(order, "price_stoplimit", 0.0),
                "sl": order.sl,
                "tp": order.tp,
                "magic": order.magic,
                "comment": order.comment,
            }
        )
    return rows


def orders_command(mt5: Any, args: argparse.Namespace) -> None:
    orders = mt5.orders_get(symbol=args.market) if args.market else mt5.orders_get()
    rows = rows_from_orders(mt5, list(orders or []))
    print_table(rows, ["ticket", "symbol", "type", "volume", "price", "stoplimit", "sl", "tp", "magic", "comment"], args.json)


def history_command(mt5: Any, args: argparse.Namespace) -> None:
    date_to = parse_datetime(args.to_date) or datetime.now()
    date_from = parse_datetime(args.from_date) or (date_to - timedelta(days=int(args.days)))
    deals = mt5.history_deals_get(date_from, date_to)
    if deals is None:
        die(f"No se pudo leer historial. last_error={mt5.last_error()}")

    deal_type_names = order_type_lookup(mt5, "DEAL_TYPE_")
    entry_names = order_type_lookup(mt5, "DEAL_ENTRY_")
    rows = []
    filtered_deals = [deal for deal in deals if not args.market or deal.symbol == args.market]
    for deal in sorted(filtered_deals, key=lambda item: item.time, reverse=True)[: max(args.last, 0)]:
        rows.append(
            {
                "ticket": deal.ticket,
                "time": datetime.fromtimestamp(deal.time).isoformat(sep=" ", timespec="seconds"),
                "symbol": deal.symbol,
                "type": deal_type_names.get(int(deal.type), deal.type),
                "entry": entry_names.get(int(deal.entry), deal.entry),
                "volume": deal.volume,
                "price": deal.price,
                "profit": deal.profit,
                "position": deal.position_id,
                "order": deal.order,
                "comment": deal.comment,
            }
        )
    print_table(rows, ["ticket", "time", "symbol", "type", "entry", "volume", "price", "profit", "position", "order", "comment"], args.json)


def account_command(mt5: Any, args: argparse.Namespace) -> None:
    account = mt5.account_info()
    if account is None:
        die(f"No se pudo leer la cuenta. last_error={mt5.last_error()}")
    data = as_dict(account)
    if args.json:
        print(json.dumps(data, default=str, indent=2, sort_keys=True))
    else:
        for key in ("login", "server", "currency", "balance", "equity", "margin", "margin_free", "leverage", "trade_allowed"):
            print(f"{key}: {data.get(key)}")


def symbol_command(mt5: Any, args: argparse.Namespace) -> None:
    info = ensure_symbol(mt5, args.market)
    tick = tick_for_symbol(mt5, args.market)
    data = {
        "symbol": args.market,
        "digits": info.digits,
        "point": info.point,
        "spread": info.spread,
        "volume_min": info.volume_min,
        "volume_max": info.volume_max,
        "volume_step": info.volume_step,
        "bid": tick.bid,
        "ask": tick.ask,
        "last": tick.last,
        "time": datetime.fromtimestamp(tick.time).isoformat(sep=" ", timespec="seconds"),
    }
    if args.json:
        print(json.dumps(data, default=str, indent=2, sort_keys=True))
    else:
        for key, value in data.items():
            print(f"{key}: {value}")


def main() -> None:
    args = parse_args()
    cmd = (args.cmd or "help").lower()

    if cmd in {"help", "-h", "--help"}:
        detailed_help()
        return

    aliases = {"hystory": "history", "positions": "opened", "pending": "orders", "delete": "cancel"}
    cmd = aliases.get(cmd, cmd)

    mt5 = initialize_mt5(args)
    try:
        if cmd == "open":
            open_order(mt5, args)
        elif cmd == "close":
            close_command(mt5, args)
        elif cmd == "edit":
            edit_command(mt5, args)
        elif cmd == "cancel":
            cancel_command(mt5, args)
        elif cmd == "opened":
            opened_command(mt5, args)
        elif cmd == "orders":
            orders_command(mt5, args)
        elif cmd == "history":
            history_command(mt5, args)
        elif cmd == "account":
            account_command(mt5, args)
        elif cmd == "symbol":
            symbol_command(mt5, args)
        else:
            die(f"Comando no reconocido: {args.cmd}. Usa --cmd=help.")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
