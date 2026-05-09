from kalshi_btc15m_bot.market.fees import estimate_entry_fee, net_edge_cents

def test_fee_non_negative():
    assert estimate_entry_fee(55.0, contracts=10) >= 0

def test_net_edge_math():
    edge = net_edge_cents(fair_value_cents=60.0, market_price_cents=54.0, fee_cents=1.0, spread_cents=2.0, slippage_cents=1.0)
    assert edge == 2.0
