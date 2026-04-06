"""Market visualization page - pure HTML/JS, reads from bridge APIs."""

PAGE_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>市场行情看板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2em;
            color: #fff;
            margin-bottom: 10px;
        }
        .header .time {
            color: #888;
            font-size: 14px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 16px;
        }
        .card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #2a2a4a;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .symbol {
            font-size: 1.3em;
            font-weight: bold;
            color: #e94560;
        }
        .state-badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
        }
        .state-TREND_UP { background: #00c853; color: #000; }
        .state-TREND_DOWN { background: #ff1744; color: #fff; }
        .state-RANGE { background: #ff9800; color: #000; }
        .state-V_SHAPE { background: #2196f3; color: #fff; }
        .state-INVERSE_V { background: #9c27b0; color: #fff; }
        .state-UNKNOWN { background: #666; color: #fff; }
        .price-row {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 8px;
        }
        .bid { font-size: 1.6em; font-weight: bold; color: #fff; }
        .ask { font-size: 1em; color: #888; margin-left: 8px; }
        .spread { font-size: 12px; color: #666; }
        .change {
            font-size: 14px;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .change-up { background: rgba(0,200,83,0.2); color: #00c853; }
        .change-down { background: rgba(255,23,68,0.2); color: #ff1744; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #2a2a4a;
        }
        .metric {
            text-align: center;
            padding: 8px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
        }
        .metric-label {
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 4px;
        }
        .metric-value {
            font-size: 14px;
            font-weight: bold;
        }
        .confidence-bar {
            height: 4px;
            background: #333;
            border-radius: 2px;
            margin-top: 8px;
            overflow: hidden;
        }
        .confidence-fill {
            height: 100%;
            border-radius: 2px;
            transition: width 0.3s;
        }
        .section-title {
            font-size: 14px;
            color: #888;
            margin: 24px 0 12px;
            padding-left: 8px;
            border-left: 3px solid #e94560;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        .error {
            text-align: center;
            padding: 20px;
            color: #ff5252;
            background: rgba(255,82,82,0.1);
            border-radius: 8px;
            margin: 20px 0;
        }
        .refresh-btn {
            background: #e94560;
            color: #fff;
            border: none;
            padding: 10px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }
        .refresh-btn:hover { background: #d63850; }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #555;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 市场行情看板</h1>
        <div class="time" id="currentTime">加载中...</div>
        <button class="refresh-btn" onclick="loadData()">🔄 刷新数据</button>
    </div>

    <div id="error" class="error" style="display:none"></div>

    <div class="section-title">🪙 贵金属 & 能源</div>
    <div class="grid" id="metalsGrid"><div class="loading">加载中...</div></div>

    <div class="section-title">💱 外汇</div>
    <div class="grid" id="forexGrid"><div class="loading">加载中...</div></div>

    <div class="section-title">📈 指数</div>
    <div class="grid" id="indicesGrid"><div class="loading">加载中...</div></div>

    <div class="section-title">₿ 加密货币</div>
    <div class="grid" id="cryptoGrid"><div class="loading">加载中...</div></div>

    <div class="footer">
        数据来源: MT5 Bridge | 每5秒自动刷新
    </div>

    <script>
        const API_BASE = '';
        const METALS = ['XAUUSD', 'XAGUSD', 'XBRUSD', 'XTIUSD', 'XNGUSD'];
        const FOREX = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCNH', 'EURJPY', 'GBPJPY', 'EURGBP', 'NZDUSD'];
        const INDICES = ['JP225', 'US500', 'US30', 'US2000', 'USTEC', 'DE40', 'HK50', 'CHINA50', 'UK100'];
        const CRYPTO = ['BTCUSD', 'ETHUSD'];

        let allData = {};
        let allStructures = {};

        async function loadData() {
            try {
                // Fetch prices and structures in parallel
                const [pricesRes, structRes] = await Promise.all([
                    fetch(API_BASE + '/csv/prices'),
                    fetch(API_BASE + '/csv/structure/all').catch(() => null)
                ]);

                if (!pricesRes.ok) throw new Error('无法获取价格数据');

                const pricesData = await pricesRes.json();
                allData = pricesData.prices || {};

                if (structRes && structRes.ok) {
                    const structData = await structRes.json();
                    allStructures = structData.structures || {};
                }

                renderCategory('metalsGrid', METALS);
                renderCategory('forexGrid', FOREX);
                renderCategory('indicesGrid', INDICES);
                renderCategory('cryptoGrid', CRYPTO);

                document.getElementById('error').style.display = 'none';
            } catch (err) {
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = '错误: ' + err.message;
            }
        }

        function renderCategory(gridId, symbols) {
            const grid = document.getElementById(gridId);
            const cards = symbols.map(s => renderCard(s)).filter(c => c).join('');
            grid.innerHTML = cards || '<div class="loading">暂无数据</div>';
        }

        function renderCard(symbol) {
            const price = allData[symbol];
            const struct = allStructures[symbol];
            if (!price) return '';

            const state = struct?.state || 'UNKNOWN';
            const confidence = struct?.confidence || 0;
            const slope = struct?.metrics?.slope || 0;
            const consistency = struct?.metrics?.consistency || 0;

            const bid = price.bid || 0;
            const ask = price.ask || 0;
            const spread = price.spread || 0;

            // Get daily change if available
            const dailyOpen = price.daily_open;
            const currentPrice = bid;
            let changePct = 0;
            let changeClass = '';
            if (dailyOpen && dailyOpen > 0) {
                changePct = ((currentPrice - dailyOpen) / dailyOpen * 100).toFixed(2);
                changeClass = changePct >= 0 ? 'change-up' : 'change-down';
                changePct = (changePct >= 0 ? '+' : '') + changePct + '%';
            } else {
                changePct = '';
            }

            const confidenceColor = confidence > 0.7 ? '#00c853' : confidence > 0.4 ? '#ff9800' : '#ff5252';

            return `
                <div class="card">
                    <div class="card-header">
                        <span class="symbol">${symbol}</span>
                        <span class="state-badge state-${state}">${stateName(state)}</span>
                    </div>
                    <div class="price-row">
                        <div>
                            <span class="bid">${bid.toFixed(priceDigits(symbol))}</span>
                            <span class="ask">${ask.toFixed(priceDigits(symbol))}</span>
                        </div>
                        ${changePct ? `<span class="change ${changeClass}">${changePct}</span>` : ''}
                    </div>
                    <div class="spread">点差: ${spread.toFixed(1)} | ${price.last_update ? timeAgo(price.last_update) : ''}</div>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-label">置信度</div>
                            <div class="metric-value" style="color:${confidenceColor}">${(confidence*100).toFixed(0)}%</div>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width:${confidence*100}%;background:${confidenceColor}"></div>
                            </div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">斜率</div>
                            <div class="metric-value">${slope > 0 ? '+' : ''}${slope.toFixed(4)}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">一致性</div>
                            <div class="metric-value">${(consistency*100).toFixed(0)}%</div>
                        </div>
                    </div>
                </div>
            `;
        }

        function stateName(state) {
            const names = {
                'TREND_UP': '单边涨',
                'TREND_DOWN': '单边跌',
                'RANGE': '震荡',
                'V_SHAPE': 'V型反转',
                'INVERSE_V': '倒V反转',
                'UNKNOWN': '未知'
            };
            return names[state] || state;
        }

        function priceDigits(symbol) {
            if (symbol.includes('JPY')) return 3;
            if (symbol.includes('USD') || symbol === 'EURUSD') return 5;
            if (symbol.includes('BTC')) return 2;
            return 2;
        }

        function timeAgo(isoTime) {
            if (!isoTime) return '';
            const diff = Date.now() - new Date(isoTime).getTime();
            const secs = Math.floor(diff / 1000);
            if (secs < 60) return secs + '秒前';
            const mins = Math.floor(secs / 60);
            return mins + '分钟前';
        }

        function updateTime() {
            document.getElementById('currentTime').textContent = new Date().toLocaleString('zh-CN');
        }

        // Init
        loadData();
        updateTime();
        setInterval(loadData, 5000);
        setInterval(updateTime, 1000);
    </script>
</body>
</html>
"""


def get_prediction_page_html() -> str:
    return PAGE_HTML
