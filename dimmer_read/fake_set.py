#!/usr/bin/env python3

class FakeSet:
    def __init__(self):
        self.value = 0
        self.write_forever()

    def write_forever(self):
        try:
            while True:
                nstr = input('Enter value: ')
                if not nstr: nstr = 100-n
                try:
                    n = float(nstr)
                except ValueError:
                    print(f'Not a number {nstr}')
                    continue
                if not (0 <= n <= 100):
                    print(f'Not a valid number in the range 0-100: {n}')
                    continue
                print(n)
                open('fakelevel.txt', 'w').write(str(n/100))
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    FakeSet()
