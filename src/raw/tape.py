import threading
import time


class Tape:
    def __init__(self):
        self.data = []
        self.head = 0

        self.lock = threading.Lock()
        self.incoming = threading.Condition(self.lock)  # Note: this is also a Lock

    def puts(self, string):
        with self.incoming:
            self.data.extend(string)
            self.incoming.notify()

    def getchar(self):
        """Wait for the next character at the tape head, consume it, and advance the tape one char to the left"""
        while True:
            try:
                char = self.peek(0)
                break
            except IndexError:
                with self.incoming:
                    self.incoming.wait()

        self.head += 1  # Move the tape one char to the left
        return char

    def _transform_slice(self, s):
        start, stop, step = s.start, s.stop, s.step
        if start is None:
            start = 0 - self.head
        if stop is None:
            stop = len(self.data) - self.head
        return slice(start + self.head, stop + self.head, step)

    def peek(self, index):
        """Get the character(s) at indices relative to the tape head"""
        with self.lock:
            if isinstance(index, slice):
                return self.data[self._transform_slice(index)]
            else:
                return self.data[index + self.head]

    def __getitem__(self, index):
        return self.peek(index)

    def cut(self, index, keep="left"):
        """Cut the tape at a relative index, keeping the left or right side"""
        with self.lock:
            if keep == "left":
                self.data = self.data[: index + self.head]
                if index < 0:
                    self.head = len(self.data)
            elif keep == "right":
                self.data = self.data[index + self.head :]
                if index > 0:
                    self.head = 0
                else:
                    self.head = min(-index, self.head)
            else:
                raise ValueError("`keep` must be 'left' or 'right'")

    def __len__(self):
        with self.lock:
            return len(self.data)

    def __str__(self):
        with self.lock:
            string = "".join(self.data)
            return string[: self.head] + "↪" + string[self.head :]

    def __repr__(self):
        string = self.__str__()
        return f'Tape("{repr(string)}", len={len(self)})'


if __name__ == "__main__":
    tape = Tape()

    def processor(tape):
        while True:
            # print(repr(tape), flush=True)
            item = tape.getchar()
            print(item, end="", flush=True)
            time.sleep(0.1)

    threading.Thread(target=processor, args=(tape,), daemon=True).start()

    tape.puts("Hello, how are you?")
    time.sleep(1)
    tape.puts(" I am fine, thank you.")
    time.sleep(1)
    tape.cut(5, keep="left")
    tape.puts("CUT LEFT")
    time.sleep(1)
    tape.cut(-10, keep="right")

    # Outputs: Hello, how are you? I am CUT LEFT

    time.sleep(3)
    print()
    print(repr(tape))
    # Outputs: Tape(I am CUT LEFT↪, len=13)
