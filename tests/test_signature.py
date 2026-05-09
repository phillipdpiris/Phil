from kalshi_btc15m_bot.clients.kalshi_rest import canonical_signing_path

def test_query_params_are_removed_from_signing_path():
    assert canonical_signing_path("/trade-api/v2/markets?status=open&limit=10") == "/trade-api/v2/markets"
