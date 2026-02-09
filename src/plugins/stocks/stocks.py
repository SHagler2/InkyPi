from plugins.base_plugin.base_plugin import BasePlugin
import yfinance as yf
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

FONT_SIZES = {
    "x-small": 0.6,
    "small": 0.8,
    "normal": 1,
    "large": 1.25,
    "x-large": 1.5
}

COUNT_SCALES = {1: 2.2, 2: 1.6, 3: 1.2, 4: 1.15, 5: 0.9, 6: 0.85}
GRID_COLUMNS = {1: 1, 2: 2, 3: 3, 4: 2, 5: 3, 6: 3}


def format_large_number(num):
    """Format large numbers with K, M, B, T suffixes."""
    if num is None:
        return "N/A"
    for threshold, suffix in [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]:
        if num >= threshold:
            return f"{num / threshold:.2f}{suffix}"
    return str(num)


def format_price(value):
    """Format a price value or return N/A."""
    return f"${value:,.2f}" if value is not None else "N/A"


class Stocks(BasePlugin):
    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params['style_settings'] = True
        return template_params

    def generate_image(self, settings, device_config):
        title = settings.get("title", "Stock Prices")
        tickers_input = settings.get("tickers", "")

        # Get saved tickers from device config
        saved_tickers_raw = device_config.get_config("stocks_saved_tickers", default=[])
        # Extract symbols from saved tickers (handle both old string format and new dict format)
        saved_tickers = [t["symbol"] if isinstance(t, dict) else t for t in saved_tickers_raw]

        # Parse comma-separated tickers from input (if any)
        input_tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()] if tickers_input else []

        # Use input tickers if provided, otherwise fall back to saved tickers
        tickers = input_tickers if input_tickers else saved_tickers

        if not tickers:
            raise RuntimeError("No tickers configured. Add tickers in the plugin settings.")

        # Fetch stock data (limit to 6 tickers)
        stocks_data = self.fetch_stock_data(tickers[:6])

        if not stocks_data:
            raise RuntimeError("Could not fetch data for any of the provided ticker symbols.")

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        stock_count = len(stocks_data)
        columns = GRID_COLUMNS.get(stock_count, 3)
        rows = (stock_count + columns - 1) // columns
        # Get auto-refresh interval for display
        auto_refresh = settings.get('autoRefresh', '0')
        try:
            auto_refresh_mins = int(auto_refresh)
        except (ValueError, TypeError):
            auto_refresh_mins = 0

        template_params = {
            "title": title,
            "stocks": stocks_data,
            "stock_count": stock_count,
            "columns": columns,
            "rows": rows,
            "last_updated": datetime.now().strftime("%I:%M %p"),
            "auto_refresh_mins": auto_refresh_mins,
            "font_scale": FONT_SIZES.get(settings.get('fontSize', 'normal'), 1),
            "count_scale": COUNT_SCALES.get(stock_count, 0.65),
            "plugin_settings": settings
        }

        image = self.render_image(dimensions, "stocks.html", "stocks.css", template_params)
        return image

    def fetch_stock_data(self, tickers):
        """Fetch stock data for a list of ticker symbols using batch request."""
        stocks_data = []

        try:
            # Batch fetch all tickers at once
            tickers_obj = yf.Tickers(" ".join(tickers))

            for symbol in tickers:
                try:
                    info = tickers_obj.tickers[symbol].info

                    # Get current price and other data
                    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
                    previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

                    if current_price is None:
                        logger.warning(f"Could not fetch price for {symbol}")
                        continue

                    # Calculate change
                    change = 0
                    change_percent = 0
                    if previous_close and current_price:
                        change = current_price - previous_close
                        change_percent = (change / previous_close) * 100

                    sign = "+" if change >= 0 else ""
                    stocks_data.append({
                        "symbol": symbol,
                        "name": info.get("shortName") or info.get("longName") or symbol,
                        "price_formatted": format_price(current_price),
                        "change_formatted": f"{sign}{change:.2f}",
                        "change_percent_formatted": f"{sign}{change_percent:.2f}%",
                        "volume": format_large_number(info.get("volume") or info.get("regularMarketVolume")),
                        "high_formatted": format_price(info.get("dayHigh") or info.get("regularMarketDayHigh")),
                        "low_formatted": format_price(info.get("dayLow") or info.get("regularMarketDayLow")),
                        "is_positive": change >= 0
                    })

                except Exception as e:
                    logger.error(f"Error processing data for {symbol}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching stock data: {str(e)}")

        return stocks_data
