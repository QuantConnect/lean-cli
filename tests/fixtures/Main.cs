using QuantConnect.Data;

namespace QuantConnect.Algorithm.CSharp
{
    public class CSharpProject : QCAlgorithm
    {
        public override void Initialize()
        {
            SetStartDate(2015, 1, 1);
            SetCash(100000);
            AddEquity("SPY", Resolution.Daily);
        }

        /// OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
        /// Slice object keyed by symbol containing the stock data
        public override void OnData(Slice data)
        {
            if (!Portfolio.Invested)
            {
                SetHoldings("SPY", 1);
                Debug("Purchased Stock");
            }
        }
    }
}
