"""Decodifica calldata de transações EVM. Dono: Dávila.
Cobre ERC-20 (transfer/approve/transferFrom/increaseAllowance) e Uniswap V2 swapExactETHForTokens.
Para ampliar: adicione entradas em SELECTORS (seletor -> nome, tipos)."""
from decimal import Decimal, localcontext

from eth_abi import decode as abi_decode
from eth_abi.exceptions import DecodingError

from api.config import ETH_USD

MAX_UINT = 2**256 - 1
UNLIMITED_THRESHOLD = 2**255  # valores absurdos também contam como "ilimitado"

# Tokens conhecidos na mainnet (endereço minúsculo -> símbolo, decimais, preço USD fixo para demo)
TOKENS = {
    "0xdac17f958d2ee523a2206206994597c13d831ec7": ("USDT", 6, 1.0),
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": ("USDC", 6, 1.0),
    "0x6b175474e89094c44da98b954eedeac495271d0f": ("DAI", 18, 1.0),
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": ("WETH", 18, ETH_USD),
}

KNOWN_CONTRACTS = {
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
}

SELECTORS = {
    "0xa9059cbb": ("transfer", ["address", "uint256"]),
    "0x095ea7b3": ("approve", ["address", "uint256"]),
    "0x23b872dd": ("transferFrom", ["address", "address", "uint256"]),
    "0x39509351": ("increaseAllowance", ["address", "uint256"]),
    "0x7ff36ab5": ("swapExactETHForTokens", ["uint256", "address[]", "address", "uint256"]),
}


def fmt_br(v: float, max_dec: int = 6) -> str:
    """1234.5 -> '1.234,5' (formato brasileiro)."""
    s = f"{v:,.{max_dec}f}"
    if max_dec:
        s = s.rstrip("0").rstrip(".")
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _human(amount: int, decimals: int) -> str:
    with localcontext() as ctx:
        ctx.prec = 100
        return fmt_br(Decimal(amount) / Decimal(10)**decimals, max_dec=decimals)


def decode_calldata(to: str, data: str, value_wei: str = "0") -> dict:
    to_l = to.lower()
    value = int(value_wei or "0")
    data = (data or "0x").lower()
    out: dict = {"action": "unknown", "function": None, "token": None, "token_symbol": None,
                 "spender": None, "recipient": None, "amount": None, "amount_usd": None,
                 "is_unlimited": False, "raw_args": None}

    if data in ("0x", ""):
        out.update(action="native_transfer", recipient=to_l, token_symbol="ETH",
                   amount=_human(value, 18), amount_usd=round(value / 1e18 * ETH_USD, 2))
        return out

    sel = data[:10]
    if sel not in SELECTORS:
        out["function"] = sel
        if value:
            out["amount"], out["token_symbol"] = _human(value, 18), "ETH"
            out["amount_usd"] = round(value / 1e18 * ETH_USD, 2)
        return out

    name, types = SELECTORS[sel]
    try:
        args = abi_decode(types, bytes.fromhex(data[10:]))
    except (DecodingError, ValueError, OverflowError):
        out["function"] = sel
        return out
    if name == "swapExactETHForTokens" and len(args[1]) < 2:
        out["function"] = sel
        return out
    out["function"] = name
    out["raw_args"] = [a if isinstance(a, (int, str)) else list(a) for a in args]

    sym, dec, price = TOKENS.get(to_l, ("TOKEN?", 18, None))

    if name in ("approve", "increaseAllowance"):
        spender, amount = args
        out.update(action="approve", token=to_l, token_symbol=sym, spender=spender.lower(),
                   is_unlimited=amount >= UNLIMITED_THRESHOLD)
        out["amount"] = "ILIMITADO" if out["is_unlimited"] else _human(amount, dec)
        if not out["is_unlimited"] and price is not None:
            out["amount_usd"] = round(amount / 10**dec * price, 2)
    elif name in ("transfer", "transferFrom"):
        recipient, amount = (args[0], args[1]) if name == "transfer" else (args[1], args[2])
        out.update(action="transfer" if name == "transfer" else "transferFrom", token=to_l,
                   token_symbol=sym, recipient=recipient.lower(), amount=_human(amount, dec))
        if price is not None:
            out["amount_usd"] = round(amount / 10**dec * price, 2)
    elif name == "swapExactETHForTokens":
        _min_out, path, recipient, _deadline = args
        out_sym = TOKENS.get(path[-1].lower(), ("TOKEN?",))[0]
        out.update(action="swap", recipient=recipient.lower(), token_symbol="ETH",
                   amount=_human(value, 18), amount_usd=round(value / 1e18 * ETH_USD, 2),
                   token=path[-1].lower())
        out["swap_out_symbol"] = out_sym
    return out


def known_contract_name(addr: str | None) -> str | None:
    if not addr:
        return None
    a = addr.lower()
    if a in KNOWN_CONTRACTS:
        return KNOWN_CONTRACTS[a]
    if a in TOKENS:
        return f"Token {TOKENS[a][0]}"
    return None
