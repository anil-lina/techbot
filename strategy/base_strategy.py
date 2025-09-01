from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    def __init__(self, api_handler, trade_settings):
        self.api = api_handler
        self.trade_settings = trade_settings

    @abstractmethod
    def generate_signals(self, data):
        """
        Analyzes the data and generates trading signals.

        :param data: DataFrame with historical data and indicators.
        :return: A signal ('BUY', 'SELL', 'HOLD') or None.
        """
        pass

    @abstractmethod
    def execute(self, instrument):
        """
        Main execution logic for the strategy for a given instrument.
        """
        pass
