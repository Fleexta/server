import random
import string


class HashManager:
    def __init__(self):
        all_symbols = string.ascii_letters + string.digits
        self.hash = ''.join(random.choice(all_symbols) for _ in range(16))
