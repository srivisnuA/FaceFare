import datetime

def log_transaction(pid, event):

    time = datetime.datetime.now()

    print(f"{pid} | {event} | {time}")