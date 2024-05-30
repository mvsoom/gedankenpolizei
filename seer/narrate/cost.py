from time import time

# Manual define pricing tiers in $/MTok (https://www.anthropic.com/api)
PRICING = {
    "haiku": {"input": 0.25, "output": 1.25},
    "sonnet": {"input": 3.00, "output": 15.00},
    "opus": {"input": 15.00, "output": 75.00},
}


class APICosts:
    def __init__(self, model_name):
        self.start = time()
        self.model = model_name.split("-")[2].lower()

        # Convert prices from $/MTok to $/tok
        self.in_price = PRICING[self.model]["input"] / 1e6
        self.out_price = PRICING[self.model]["output"] / 1e6

        self.in_total = 0
        self.out_total = 0

    def ingest(self, response):
        self.in_total += response.usage.input_tokens
        self.out_total += response.usage.output_tokens

    def current_costs(self):
        dt = time() - self.start
        total = self.in_total * self.in_price + self.out_total * self.out_price
        rate = total / dt * 3600
        return total, rate

    def log_current_costs(self, logging_func):
        total, rate = self.current_costs()
        logging_func(f"API cost({self.model}): ${rate:.2f}/hour (total: ${total:.4f})")