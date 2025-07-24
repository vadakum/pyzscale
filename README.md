Welcome to **pyzscale**! 🎉

### Intended audience:
This is an example project for a hobbyist algo-trader or a developer looking to dive into the world of automated trading. 

### What is the project about
I am a C++ developer who started liking Python for its versatility. My trader friend wanted to automate his "secret sauce" trading logic – a sort of weighing balance (hence the project name, pyzscale, because "weighing_balance_bot" just didn't roll off the tongue). He needed something to play nice with broker APIs and their REST-based services and WebSockets. "Aha!" I thought, "This could be perfect way to learn more about Python and its babies (the packages)!". 
Btw, this entire thing took ~3 Months to build (@ ~4 hours per day). Due to time constraints there is no documentation, I guess now the AI tools can quickly generate them for you.

Now, fair warning: if you're a Python purist, you might find my code a tad... un-pythonic. But anyways, I loved coding the entire thing. 

### Key Features

*   **Live Trading Bot**: A multi-process, bot designed for live market operations.
*   **Mini and custom Backtesting Engine**: A very use case specific backtester.
*   **Real-time Market Data**: Efficiently processes and distributes streaming (over the internet) market data, including complex option chains.
*   **Strategy & Signal Generation**: A modular service for developing and integrating your own alpha-generating models.
*   **Order & Position Management**: Working example of complete system for managing orders, tracking positions, and calculating PnL in real-time.
*   **Kite Connect Integration**: Includes a wrapper for the Zerodha Kite Connect API.
*   **Data Analysis**: Comes with a suite of Jupyter notebooks for research, tuning, and visualizing backtest results.
*   **Powered by the Best**: We stand on the shoulders of giants! Built with libraries like `pandas`, `numpy`, `redis`, `asyncio`, `httpx`, `psycopg` and `redis` for high performance. Because performance matters, even when you're just trading imaginary money.

### License

This project is released into the public domain. See the **UNLICENSE.txt** file for details.

---

Feel free to explore, fork, and build upon it. May your code compile on the first try and your trades hit their targets! Happy building trading alpha and strategies!
