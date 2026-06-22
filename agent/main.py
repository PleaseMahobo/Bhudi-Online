import time
from collector import collect
from client import send

def run():
    while True:
        data = collect()
        res = send(data)
        print(res.status_code, res.text)
        time.sleep(30)

if __name__ == "__main__":
    run()